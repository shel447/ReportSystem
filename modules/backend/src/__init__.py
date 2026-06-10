"""ReportSystem runtime registration entrypoint."""

from .controllers import ChatController, HealthCheckController, ReportController, TemplateController
from .infrastructure.chatbi_server import ChatBIServer

_server = ChatBIServer()


def register_initialize() -> None:
    _server.initialize()


def register_handler() -> list[object]:
    return [
        ChatController(_server),
        TemplateController(_server),
        ReportController(_server),
        HealthCheckController(),
    ]


def register_destroy() -> None:
    _server.destroy()
