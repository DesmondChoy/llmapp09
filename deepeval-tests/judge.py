"""DeepEval judge using the same Ollama Cloud credentials as the application."""

import asyncio
import json
import os
import re
from functools import lru_cache

import requests
from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel


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
        response = requests.post(
            f"{self.base_url}/api/chat",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        response.raise_for_status()
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
