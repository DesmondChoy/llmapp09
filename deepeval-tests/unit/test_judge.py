import asyncio
import importlib
import json
import sys
from unittest.mock import Mock

import pytest
import requests
from deepeval.metrics import GEval
from pydantic import BaseModel, ValidationError

import api_client
import judge


class Verdict(BaseModel):
    score: float
    reason: str


@pytest.fixture(autouse=True)
def configure_judge(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_API_KEY", "test-ollama-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com/")
    monkeypatch.delenv("DEEPEVAL_OLLAMA_MODEL", raising=False)
    judge.get_judge.cache_clear()
    yield
    judge.get_judge.cache_clear()


def test_requires_ollama_key(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY")
    with pytest.raises(ValueError, match="OLLAMA_API_KEY"):
        judge.get_judge()


@pytest.mark.parametrize("async_mode", [False, True])
def test_cloud_request_and_validated_response(monkeypatch, async_mode):
    response = Mock()
    response.json.return_value = {
        "message": {"content": '```json\n{"score": 1, "reason": "Correct"}\n```'}
    }
    post = Mock(return_value=response)
    monkeypatch.setattr(judge.requests, "post", post)
    model = judge.get_judge()
    result = (
        asyncio.run(model.a_generate("Assess the output.", Verdict))
        if async_mode else model.generate("Assess the output.", Verdict)
    )
    assert result == Verdict(score=1, reason="Correct")
    args, kwargs = post.call_args
    assert args == ("https://ollama.com/api/chat",)
    assert kwargs["headers"]["Authorization"] == "Bearer test-ollama-key"
    body = kwargs["json"]
    assert body["model"] == "gemma4:31b"
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert "format" not in body
    assert json.dumps(Verdict.model_json_schema()) in body["messages"][0]["content"]
    response.raise_for_status.assert_called_once()


def test_model_override_and_default_endpoint(monkeypatch):
    monkeypatch.setenv("DEEPEVAL_OLLAMA_MODEL", "glm-5.2")
    monkeypatch.setenv("OLLAMA_BASE_URL", "")
    model = judge.get_judge()
    assert model.name == "glm-5.2"
    assert model.base_url == "https://ollama.com"


@pytest.mark.parametrize("content", ["not JSON", '{"score": "invalid"}'])
def test_invalid_judge_response_fails(monkeypatch, content):
    response = Mock()
    response.json.return_value = {"message": {"content": content}}
    monkeypatch.setattr(judge.requests, "post", Mock(return_value=response))
    with pytest.raises(ValidationError):
        judge.get_judge().generate("Assess the output.", Verdict)


def test_cloud_http_error_is_not_scored(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
    monkeypatch.setattr(judge.requests, "post", Mock(return_value=response))
    with pytest.raises(requests.HTTPError):
        judge.get_judge().generate("Assess the output.", Verdict)
    response.json.assert_not_called()


def test_every_suite_uses_cloud_judge_without_openai(monkeypatch):
    # Suites fetch application responses at import time. Stub only those calls
    # so this test can inspect every real metric without contacting a backend.
    for name in ["classify_text", "analyze_sentiment", "summarize_text", "detect_intent"]:
        monkeypatch.setattr(api_client, name, lambda text: {})
    for name, count in [("test_classify", 3), ("test_sentiment", 4),
                        ("test_summarize", 5), ("test_intent", 4)]:
        previous = sys.modules.pop(name, None)
        try:
            module = importlib.import_module(name)
            metrics = [value for value in vars(module).values() if isinstance(value, GEval)]
            assert len(metrics) == count
            assert all(metric.model is judge.get_judge() for metric in metrics)
        finally:
            sys.modules.pop(name, None)
            if previous is not None:
                sys.modules[name] = previous
