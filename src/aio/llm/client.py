from __future__ import annotations

import json
from urllib import error, request

from aio.config.schema import Config


class LLMClient:
    def __init__(self, config: Config):
        self.config = config

    def complete(self, prompt: str) -> str:
        # V1 scaffold returns deterministic mock output.
        return f"[{self.config.model_provider}/{self.config.model_name}] {prompt}"


class LlamaCppClient(LLMClient):
    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        url = self.config.model_base_url.rstrip("/") + "/v1/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.config.model_timeout_seconds) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(
                "Failed to reach llama.cpp server. "
                f"base_url={self.config.model_base_url}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON response from llama.cpp server") from exc

        try:
            return str(parsed["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Unexpected llama.cpp response format from /v1/chat/completions"
            ) from exc
