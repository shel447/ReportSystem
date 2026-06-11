from __future__ import annotations

from requests import Response, Session

from src.infrastructure.platform.client import RuntimeHttpClient


class RecordingSession(Session):
    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response
        self.calls: list[dict] = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


def test_runtime_http_client_passes_relative_platform_path_and_user_header():
    response = Response()
    response.status_code = 200
    response._content = b'{"ok": true}'
    session = RecordingSession(response)

    result = RuntimeHttpClient(session=session).post_json(
        path_or_url="/rest/platform/demo",
        payload={"value": 1},
        user_id="user-1",
    )

    assert result == {"ok": True}
    assert session.calls[0]["url"] == "/rest/platform/demo"
    assert session.calls[0]["headers"]["X-User-Id"] == "user-1"
    assert response.raw is None or response.raw.closed
