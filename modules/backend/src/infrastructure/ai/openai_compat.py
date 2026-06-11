from __future__ import annotations

import codecs
from dataclasses import dataclass
import json
from typing import Any, Dict, List, Sequence

from requests import Response, Session
from requests.exceptions import RequestException, Timeout
from runtime.client._session import GLOBAL_HTTP_SESSION

from ...shared.agentflow.metrics import record_llm_usage
from ...shared.kernel.errors import ErrorCode, UpstreamError


class AIRequestError(Exception):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    model: str
    api_key: str = ""
    timeout_sec: int = 60
    temperature: float = 0.2
    infer_params: Dict[str, Any] | None = None


class OpenAICompatGateway:
    def __init__(self, *, session: Session | None = None) -> None:
        self.session = session or GLOBAL_HTTP_SESSION

    def chat_completion(
        self,
        config: ProviderConfig,
        messages: Sequence[Dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = dict(config.infer_params or {})
        payload["model"] = config.model
        payload["messages"] = list(messages)
        if temperature is not None:
            payload["temperature"] = temperature
        else:
            payload.setdefault("temperature", config.temperature)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = self._post(
            config,
            "/chat/completions",
            payload,
            stream=bool(payload.get("stream", False)),
        )
        record_llm_usage(data)
        try:
            choice = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise UpstreamError(
                "Completion 接口返回格式无效。",
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="openai_compatible",
                http_status=502,
            ) from exc
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
            raise UpstreamError(
                "Embedding 接口返回格式无效。",
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="openai_compatible",
                http_status=502,
            ) from exc

        vectors: List[List[float]] = []
        for item in items:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise UpstreamError(
                    "Embedding 接口返回的向量格式无效。",
                    error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                    source="openai_compatible",
                    http_status=502,
                )
            vectors.append([float(value) for value in embedding])
        return vectors

    def _post(
        self,
        config: ProviderConfig,
        path: str,
        payload: Dict[str, Any],
        *,
        stream: bool = False,
    ) -> Dict[str, Any]:
        url = config.base_url.rstrip("/") + path
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        try:
            response = self.session.post(
                url=url,
                headers=headers,
                json=payload,
                stream=stream,
                timeout=config.timeout_sec,
            )
        except Timeout as exc:
            raise UpstreamError(
                f"上游接口请求超时：{url}",
                error_code=ErrorCode.BASE_OVERTIME,
                source="openai_compatible",
                retryable=True,
                http_status=504,
            ) from exc
        except RequestException as exc:
            raise UpstreamError(
                f"上游接口调用失败：{exc}",
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="openai_compatible",
                retryable=True,
                http_status=502,
            ) from exc

        try:
            if response.status_code >= 400:
                self._raise_http_error(response)
            if stream:
                return self._read_stream(response, fallback_model=config.model)
            try:
                return response.json()
            except ValueError as exc:
                raise UpstreamError(
                    "上游接口未返回合法 JSON。",
                    error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                    source="openai_compatible",
                    http_status=502,
                ) from exc
        finally:
            response.close()

    def _read_stream(self, response: Response, *, fallback_model: str) -> Dict[str, Any]:
        decoder = codecs.getincrementaldecoder("utf-8")()
        buffer = ""
        content: list[str] = []
        model = fallback_model
        usage: dict[str, Any] = {}

        def consume(line: str) -> None:
            nonlocal model, usage
            stripped = line.strip()
            if not stripped or stripped.startswith(":"):
                return
            raw = stripped[5:].strip() if stripped.startswith("data:") else stripped
            if raw == "[DONE]":
                return
            try:
                event = json.loads(raw)
            except ValueError as exc:
                raise UpstreamError(
                    "流式 Completion 接口返回了非法事件。",
                    error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                    source="openai_compatible",
                    http_status=502,
                ) from exc
            if not isinstance(event, dict):
                return
            model = str(event.get("model") or model)
            if isinstance(event.get("usage"), dict):
                usage = dict(event["usage"])
            choices = event.get("choices")
            if not isinstance(choices, list) or not choices:
                return
            choice = choices[0] if isinstance(choices[0], dict) else {}
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            value = delta.get("content")
            if value is None and isinstance(choice.get("message"), dict):
                value = choice["message"].get("content")
            if isinstance(value, str):
                content.append(value)

        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            buffer += decoder.decode(chunk)
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                consume(line.rstrip("\r"))
        buffer += decoder.decode(b"", final=True)
        if buffer.strip():
            consume(buffer)
        return {
            "model": model,
            "choices": [{"message": {"content": "".join(content)}}],
            "usage": usage,
        }

    def _raise_http_error(self, response: Response) -> None:
        body = (response.text or "").strip().replace("\n", " ")
        if len(body) > 240:
            body = body[:240] + "..."
        detail = body or f"HTTP {response.status_code}"
        raise UpstreamError(
            f"上游接口返回错误（{response.status_code}）：{detail}",
            details=_upstream_details(response),
            error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
            source="openai_compatible",
            retryable=response.status_code >= 500,
            http_status=502,
        )

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


def _upstream_details(response: Response) -> dict[str, Any]:
    details: dict[str, Any] = {"statusCode": response.status_code}
    try:
        payload = response.json()
    except ValueError:
        return details
    if isinstance(payload, dict):
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        code = payload.get("errorCode") or payload.get("code") or error.get("code")
        message = payload.get("errorMsg") or payload.get("message") or error.get("message")
        if code:
            details["upstreamCode"] = str(code)
        if message:
            details["upstreamMessage"] = str(message)
    return details
