"""Platform configuration-related external adapters."""

from __future__ import annotations

from .client import RuntimeHttpClient


class ExternalMetadataSyncGateway:
    def __init__(self, *, client: RuntimeHttpClient) -> None:
        self.client = client

    def check_package_register_process(self) -> dict[str, Any]:
        return self.client.get_json(path_or_url="/rest/entassistantservice/v1/chatbi/package/register/process")
