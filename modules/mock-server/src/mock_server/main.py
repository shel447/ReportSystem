"""可插拔开发态外部业务服务替身。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = PROJECT_ROOT / "testdata" / "mock-server" / "responses.json"


def _load_fixtures() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _apply_scenario(scenario: str | None, *, empty: Any) -> Any | None:
    if scenario == "timeout":
        raise HTTPException(status_code=504, detail="mock timeout")
    if scenario == "error":
        raise HTTPException(status_code=500, detail="mock error")
    return empty if scenario == "empty" else None


def _dataset_response(dataset: dict[str, Any]) -> dict[str, Any]:
    return {"retCode": 0, "retInfo": "", "data": dataset}


def _dataset_business_error() -> dict[str, Any]:
    return {"retCode": 1001, "retInfo": "mock dataset business error"}


def create_app() -> FastAPI:
    app = FastAPI(title="ReportSystem Mock External Service")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/chat/completions")
    def chat_completions(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty="")
        content = empty if empty is not None else "completion test ok"
        return {"model": payload.get("model") or "mock-chat", "choices": [{"message": {"content": content}}]}

    @app.post("/v1/embeddings")
    def embeddings(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty=[])
        inputs = list(payload.get("input") or [])
        vectors = empty if empty is not None else [_embedding(str(item)) for item in inputs]
        return {"model": payload.get("model") or "mock-embedding", "data": [{"embedding": item} for item in vectors]}

    @app.post("/rest/parameter-options/{name}")
    def parameter_options(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty={"options": [], "defaultValue": []})
        if empty is not None:
            return empty
        values = _load_fixtures()["parameterOptions"].get(name)
        if values is None:
            raise HTTPException(status_code=404, detail=f"unknown parameter options: {name}")
        return values

    @app.post("/rest/onequery")
    def onequery(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        if x_mock_scenario == "business-error":
            return _dataset_business_error()
        empty = _apply_scenario(x_mock_scenario, empty=_dataset_response({"columns": {}, "results": []}))
        if empty is not None:
            return empty
        query = str(payload.get("query") or "").lower()
        key = next((item for item in _load_fixtures()["queryMatches"] if item in query), "default")
        return _dataset_response(_load_fixtures()["datasets"][key])

    @app.post("/rest/datasets/{name}")
    def api_dataset(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        if x_mock_scenario == "business-error":
            return _dataset_business_error()
        empty = _apply_scenario(x_mock_scenario, empty=_dataset_response({"columns": {}, "results": []}))
        if empty is not None:
            return empty
        dataset = _load_fixtures()["datasets"].get(name)
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"unknown dataset: {name}")
        return _dataset_response(dataset)

    @app.post("/rest/dynamic-content/{name}")
    def dynamic_content(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty={"status": "success", "dsl": [], "meta": {"dslType": "Components"}})
        if empty is not None:
            return empty
        payload = _load_fixtures()["dynamicContent"].get(name)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"unknown dynamic content: {name}")
        return payload

    return app


def _embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round((value - 127.5) / 127.5, 6) for value in digest[:8]]


app = create_app()
