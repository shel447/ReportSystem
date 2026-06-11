"""Shared requests session compatible with the platform runtime SDK."""

from __future__ import annotations

import os
from urllib.parse import urljoin

from requests import PreparedRequest, Request, Session


class RuntimeSession(Session):
    """Resolve platform-relative URLs for local development."""

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", float(os.getenv("RUNTIME_CLIENT_TIMEOUT_SECONDS") or 10))
        return super().request(method, url, **kwargs)

    def prepare_request(self, request: Request) -> PreparedRequest:
        request.url = self._resolve_url(str(request.url or ""))
        authorization = str(os.getenv("RUNTIME_CLIENT_AUTHORIZATION") or "").strip()
        if authorization and not (request.headers or {}).get("Authorization"):
            request.headers = dict(request.headers or {})
            request.headers["Authorization"] = authorization
        return super().prepare_request(request)

    @staticmethod
    def _resolve_url(url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        if not url.startswith("/"):
            raise ValueError(f"runtime client relative url must start with /: {url}")
        base_url = str(os.getenv("RUNTIME_CLIENT_BASE_URL") or "http://127.0.0.1:8310").strip()
        return urljoin(f"{base_url.rstrip('/')}/", url.lstrip("/"))


GLOBAL_HTTP_SESSION: Session = RuntimeSession()
