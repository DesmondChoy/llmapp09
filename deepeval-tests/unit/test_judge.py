import asyncio
import importlib
import json
import sys
from unittest.mock import Mock, call

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


@pytest.fixture(autouse=True)
def retry_sleep(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(judge.time, "sleep", sleep)
    return sleep


def judge_response(status=200, content='{"score": 1, "reason": "Correct"}'):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({"message": {"content": content}}).encode()
    response._content_consumed = True
    response.url = "https://ollama.com/api/chat"
    return response


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
    assert kwargs["timeout"] == (10, 120)
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
def test_invalid_judge_response_fails(monkeypatch, retry_sleep, content):
    response = Mock()
    response.json.return_value = {"message": {"content": content}}
    post = Mock(return_value=response)
    monkeypatch.setattr(judge.requests, "post", post)
    with pytest.raises(ValidationError):
        judge.get_judge().generate("Assess the output.", Verdict)
    post.assert_called_once()
    retry_sleep.assert_not_called()


def test_cloud_http_error_is_not_scored(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
    monkeypatch.setattr(judge.requests, "post", Mock(return_value=response))
    with pytest.raises(requests.HTTPError):
        judge.get_judge().generate("Assess the output.", Verdict)
    response.json.assert_not_called()


@pytest.mark.parametrize("async_mode", [False, True])
def test_recovers_from_transport_failures(monkeypatch, retry_sleep, caplog, async_mode):
    post = Mock(side_effect=[
        requests.ReadTimeout("private request details"),
        requests.ConnectionError("private request details"),
        judge_response(),
    ])
    monkeypatch.setattr(judge.requests, "post", post)
    model = judge.get_judge()
    result = (
        asyncio.run(model.a_generate("Assess the output.", Verdict))
        if async_mode else model.generate("Assess the output.", Verdict)
    )
    assert result == Verdict(score=1, reason="Correct")
    assert post.call_count == 3
    assert retry_sleep.call_args_list == [call(2), call(4)]
    # Each attempt must judge the same input with the same settings.
    assert post.call_args_list == [post.call_args_list[0]] * 3
    assert "attempt 2/3" in caplog.text and "attempt 3/3" in caplog.text
    assert "private request details" not in caplog.text
    assert "test-ollama-key" not in caplog.text
    assert "Assess the output." not in caplog.text


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_recovers_from_temporary_http_errors(monkeypatch, retry_sleep, status):
    failed = judge_response(status)
    close = Mock(wraps=failed.close)
    monkeypatch.setattr(failed, "close", close)
    post = Mock(side_effect=[failed, judge_response()])
    monkeypatch.setattr(judge.requests, "post", post)
    assert judge.get_judge().generate("Assess.", Verdict).score == 1
    assert post.call_count == 2
    retry_sleep.assert_called_once_with(2)
    close.assert_called_once()


@pytest.mark.parametrize("error_type", [requests.ReadTimeout, requests.ConnectTimeout,
                                        requests.ConnectionError])
def test_transport_retry_exhaustion_raises_last_error(monkeypatch, retry_sleep, error_type):
    errors = [error_type(f"attempt {n}") for n in range(3)]
    post = Mock(side_effect=errors)
    monkeypatch.setattr(judge.requests, "post", post)
    with pytest.raises(error_type) as caught:
        judge.get_judge().generate("Assess.", Verdict)
    assert caught.value is errors[-1]
    assert post.call_count == 3
    assert retry_sleep.call_args_list == [call(2), call(4)]


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_http_retry_exhaustion_raises_last_error(monkeypatch, retry_sleep, status):
    responses = [judge_response(status) for _ in range(3)]
    post = Mock(side_effect=responses)
    monkeypatch.setattr(judge.requests, "post", post)
    with pytest.raises(requests.HTTPError) as caught:
        judge.get_judge().generate("Assess.", Verdict)
    assert caught.value.response is responses[-1]
    assert post.call_count == 3
    assert retry_sleep.call_args_list == [call(2), call(4)]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 501])
def test_permanent_http_errors_fail_immediately(monkeypatch, retry_sleep, status):
    post = Mock(return_value=judge_response(status))
    monkeypatch.setattr(judge.requests, "post", post)
    with pytest.raises(requests.HTTPError):
        judge.get_judge().generate("Assess.", Verdict)
    post.assert_called_once()
    retry_sleep.assert_not_called()


def test_certificate_error_fails_immediately(monkeypatch, retry_sleep):
    post = Mock(side_effect=requests.exceptions.SSLError("Invalid certificate"))
    monkeypatch.setattr(judge.requests, "post", post)
    with pytest.raises(requests.exceptions.SSLError):
        judge.get_judge().generate("Assess.", Verdict)
    post.assert_called_once()
    retry_sleep.assert_not_called()


def test_low_score_is_returned_without_retry(monkeypatch, retry_sleep):
    post = Mock(return_value=judge_response(content='{"score": 0, "reason": "Incorrect"}'))
    monkeypatch.setattr(judge.requests, "post", post)
    assert judge.get_judge().generate("Assess.", Verdict) == Verdict(score=0, reason="Incorrect")
    post.assert_called_once()
    retry_sleep.assert_not_called()


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
