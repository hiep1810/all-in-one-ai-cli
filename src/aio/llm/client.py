from __future__ import annotations

import json
from collections.abc import Iterator
from urllib import error, request

from aio.config.schema import Config


class LLMClient:
    def __init__(self, config: Config):
        self.config = config

    def complete(self, prompt: str, system_prompt: str = "") -> str:
        # V1 scaffold returns deterministic mock output.
        # system_prompt is accepted but intentionally ignored in the mock
        # so tests don't need to change when the real client is swapped in.
        return f"[{self.config.model_provider}/{self.config.model_name}] {prompt}"

    def stream_complete(self, prompt: str, system_prompt: str = "") -> Iterator[str]:
        yield self.complete(prompt, system_prompt=system_prompt)


class LlamaCppClient(LLMClient):
    def complete(self, prompt: str, system_prompt: str = "") -> str:
        payload = self._payload(prompt, stream=False, system_prompt=system_prompt)
        parsed = self._post_json(payload)

        try:
            return str(parsed["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Unexpected llama.cpp response format from /v1/chat/completions"
            ) from exc

    def stream_complete(self, prompt: str, system_prompt: str = "") -> Iterator[str]:
        payload = self._payload(prompt, stream=True, system_prompt=system_prompt)
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
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    done, chunk = parse_stream_data(line[5:].strip())
                    if done:
                        break
                    if chunk:
                        yield chunk
        except error.URLError as exc:
            raise RuntimeError(
                "Failed to reach llama.cpp server. "
                f"base_url={self.config.model_base_url}"
            ) from exc

    def _payload(self, prompt: str, stream: bool, system_prompt: str = "") -> dict[str, object]:
        # Build the messages list. The system role comes first (if any),
        # followed by the user turn.
        # Why a list of dictionaries? This {"role": ..., "content": ...} structure
        # is the industry standard (OpenAI format). By standardizing on this data
        # structure, switching between OpenAI, Anthropic, llama.cpp, and vLLM
        # becomes trivially easy without rewriting the core engine.
        messages: list[dict[str, str]] = []
        if system_prompt:
            # Junior tip: The "system" role is like standing orders for the AI.
            # It sets boundaries, personas, and persistent context which the AI
            # will always respect but usually won't explicitly reply to.
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": 0.2,
            "stream": stream,
        }
        return payload

    def _post_json(self, payload: dict[str, object]) -> dict[str, object]:
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

        return parsed


def parse_stream_data(data: str) -> tuple[bool, str]:
    if data == "[DONE]":
        return True, ""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return False, ""
    try:
        content = parsed["choices"][0]["delta"].get("content", "")
        return False, str(content)
    except (KeyError, IndexError, TypeError):
        return False, ""
