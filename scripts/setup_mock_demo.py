#!/usr/bin/env python3
"""显式导入开发态复杂模板，并把 AI 设置指向独立 mock-server。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "testdata" / "report-templates"
TEMPLATE_NAMES = [
    "network-device-health-inspection-flow.json",
    "network-device-health-inspection-paged.json",
    "network-operations-status-flow.json",
    "network-operations-status-paged.json",
]


def request_json(method: str, url: str, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers={"Content-Type": "application/json", "X-User-Id": "demo"})
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-system-url", default="http://127.0.0.1:8300")
    parser.add_argument("--mock-url", default="http://127.0.0.1:8310")
    args = parser.parse_args()
    api = args.report_system_url.rstrip("/")
    for name in TEMPLATE_NAMES:
        template = json.loads((TEMPLATE_DIR / name).read_text(encoding="utf-8"))
        detail_url = f"{api}/rest/chatbi/v1/templates/detail?{urlencode({'templateId': template['id']})}"
        existing = request_json("GET", detail_url)
        method = "PUT" if existing else "POST"
        request_json(method, detail_url if existing else f"{api}/rest/chatbi/v1/templates", template)
        print(f"{method} {template['id']}")
    request_json(
        "PUT",
        f"{api}/rest/dev/system-settings",
        {
            "completion": {"base_url": f"{args.mock_url.rstrip('/')}/v1", "model": "mock-chat", "api_key": "mock-key"},
            "embedding": {"base_url": f"{args.mock_url.rstrip('/')}/v1", "model": "mock-embedding", "api_key": "mock-key"},
        },
    )
    print("configured mock AI settings")


if __name__ == "__main__":
    main()
