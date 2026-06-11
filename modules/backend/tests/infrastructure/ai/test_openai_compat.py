from __future__ import annotations

import json

from src.infrastructure.ai.openai_compat import OpenAICompatGateway, ProviderConfig


class FakeResponse:
    def __init__(self, *, payload=None, chunks=(), status_code=200):
        self.payload = payload
        self.chunks = list(chunks)
        self.status_code = status_code
        self.closed = False
        self.text = json.dumps(payload or {})

    def json(self):
        return self.payload

    def iter_content(self, chunk_size):
        assert chunk_size == 8192
        yield from self.chunks

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_completion_uses_runtime_session_and_candidate_infer_params():
    response = FakeResponse(
        payload={
            "model": "qwen3-32b",
            "choices": [{"message": {"content": "完成"}}],
        }
    )
    session = FakeSession(response)
    gateway = OpenAICompatGateway(session=session)

    result = gateway.chat_completion(
        ProviderConfig(
            base_url="https://model.example/v1",
            model="qwen3-32b",
            infer_params={"stream": False, "temperature": 0.4, "top_p": 0.8},
        ),
        [{"role": "user", "content": "生成摘要"}],
        temperature=0.6,
        max_tokens=256,
    )

    assert result["content"] == "完成"
    assert session.calls == [
        {
            "url": "https://model.example/v1/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "json": {
                "stream": False,
                "temperature": 0.6,
                "top_p": 0.8,
                "model": "qwen3-32b",
                "messages": [{"role": "user", "content": "生成摘要"}],
                "max_tokens": 256,
            },
            "stream": False,
            "timeout": 60,
        }
    ]
    assert response.closed is True


def test_streaming_completion_aggregates_events_and_closes_response():
    response = FakeResponse(
        chunks=[
            b'data: {"model":"qwen3-32b","choices":[{"delta":{"content":"\xe7\xbd\x91',
            b'\xe7\xbb\x9c"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":"\xe7\xa8\xb3\xe5\xae\x9a"}}],',
            b'"usage":{"completion_tokens":2}}\n\n',
            b"data: [DONE]\n\n",
        ]
    )
    session = FakeSession(response)
    gateway = OpenAICompatGateway(session=session)

    result = gateway.chat_completion(
        ProviderConfig(
            base_url="https://model.example/v1",
            model="qwen3-32b",
            infer_params={"stream": True},
        ),
        [{"role": "user", "content": "分析网络状态"}],
    )

    assert result["content"] == "网络稳定"
    assert result["raw"]["usage"] == {"completion_tokens": 2}
    assert session.calls[0]["stream"] is True
    assert response.closed is True
