"""DeepEval judge using the same Ollama Cloud credentials as the application."""

import asyncio
import json
import logging
import os
import re
import time
from functools import lru_cache

import requests
from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel


logger = logging.getLogger(__name__)
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


class OllamaCloudJudge(DeepEvalBaseLLM):
    def __init__(self):
        self.api_key = os.getenv("OLLAMA_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("Set OLLAMA_API_KEY to use the Ollama Cloud judge.")
        self.base_url = (os.getenv("OLLAMA_BASE_URL") or "https://ollama.com").rstrip("/")
        model = os.getenv("DEEPEVAL_OLLAMA_MODEL") or "gemma4:31b"
        super().__init__(model=model)

    def load_model(self):
        return self.name

    def get_model_name(self):
        return f"{self.name} (Ollama Cloud)"

    def generate(self, prompt: str, schema: type[BaseModel] | None = None):
        # Ollama Cloud does not support the API's structured-output format field.
        # Ask for the schema in the prompt, then validate the response locally.
        if schema is not None:
            prompt += (
                "\n\nReturn ONLY a JSON object matching this JSON schema. "
                "Do not include Markdown fences or commentary.\n"
                + json.dumps(schema.model_json_schema())
            )
        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.name,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0},
                    },
                    timeout=(10, 120),
                )
                response.raise_for_status()
                break
            except requests.exceptions.SSLError:
                # Certificate/configuration errors need intervention.
                raise
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
                failure = type(exc).__name__
                if isinstance(exc, requests.HTTPError):
                    if exc.response is None or exc.response.status_code not in RETRYABLE_HTTP_STATUSES:
                        raise
                    failure = f"HTTP {exc.response.status_code}"
                    exc.response.close()
                if attempt == MAX_REQUEST_ATTEMPTS:
                    raise
                delay = 2 ** attempt
                logger.warning(
                    "Ollama judge request failed (%s); retrying in %s seconds (attempt %s/%s).",
                    failure, delay, attempt + 1, MAX_REQUEST_ATTEMPTS,
                )
                time.sleep(delay)
        # Invalid responses and low scores must not trigger another model call.
        content = response.json()["message"]["content"].strip()
        if schema is None:
            return content
        fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if fenced:
            content = fenced.group(1).strip()
        return schema.model_validate_json(content)

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):
        return await asyncio.to_thread(self.generate, prompt, schema)


@lru_cache(maxsize=1)
def get_judge() -> OllamaCloudJudge:
    return OllamaCloudJudge()
