from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import httpx


class AIConfigurationError(Exception):
    pass


class AIRequestError(Exception):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    model: str
    api_key: str
    timeout_sec: int = 60
    temperature: float = 0.2


class OpenAICompatGateway:
    def chat_completion(
        self,
        config: ProviderConfig,
        messages: Sequence[Dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": config.model,
            "messages": list(messages),
            "temperature": config.temperature if temperature is None else temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = self._post(config, "/chat/completions", payload)
        try:
            choice = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIRequestError("Completion 接口返回格式无效。") from exc
        return {
            "content": self._coerce_text(choice),
            "model": data.get("model") or config.model,
            "raw": data,
        }

    def create_embedding(self, config: ProviderConfig, inputs: Sequence[str]) -> List[List[float]]:
        payload = {
            "model": config.model,
            "input": list(inputs),
        }
        data = self._post(config, "/embeddings", payload)
        try:
            items = data["data"]
        except KeyError as exc:
            raise AIRequestError("Embedding 接口返回格式无效。") from exc

        vectors: List[List[float]] = []
        for item in items:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise AIRequestError("Embedding 接口返回的向量格式无效。")
            vectors.append([float(value) for value in embedding])
        return vectors

    def _post(self, config: ProviderConfig, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = config.base_url.rstrip("/") + path
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=config.timeout_sec) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIRequestError(f"上游接口请求超时：{url}") from exc
        except httpx.HTTPError as exc:
            raise AIRequestError(f"上游接口调用失败：{exc}") from exc

        if response.status_code >= 400:
            body = (response.text or "").strip().replace("\n", " ")
            if len(body) > 240:
                body = body[:240] + "..."
            detail = body or f"HTTP {response.status_code}"
            raise AIRequestError(f"上游接口返回错误（{response.status_code}）：{detail}")

        try:
            return response.json()
        except ValueError as exc:
            raise AIRequestError("上游接口未返回合法 JSON。") from exc

    def _coerce_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            chunks: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())
            return "\n".join(chunks).strip()
        return str(content or "").strip()
