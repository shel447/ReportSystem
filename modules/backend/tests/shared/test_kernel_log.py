from __future__ import annotations

import time

from src.shared.kernel.log import (
    LOG_METHODS,
    LogLevelMonitor,
    _configure_logger,
    _escape_for_log,
    _mask_sensitive,
    _patch_log_method,
)


class _RecordingLogger:
    def __init__(self):
        self.depth = 0
        self.calls = []
        for name in LOG_METHODS:
            setattr(self, name, self._record(name))

    def _record(self, name):
        def record(message, *args, **kwargs):
            self.calls.append((name, message, args, kwargs))

        return record


def test_log_values_escape_control_characters_and_mask_sensitive_fields():
    value = "line1\nline2\ttoken=abcdef password: secret ssl.key.password=kafka"

    sanitized = _mask_sensitive(_escape_for_log(value))

    assert sanitized == r"line1\nline2\ttoken=a****** password: s****** ssl.key.password=k******"


def test_log_method_sanitizes_message_args_and_kwargs():
    calls = []
    patched = _patch_log_method(lambda message, *args, **kwargs: calls.append((message, args, kwargs)))

    patched("token=abcdef\nnext", "password=secret", extra="cookie=session-value")

    assert calls == [
        (
            r"token=a******\nnext",
            ("password=s******",),
            {"extra": "cookie=s******"},
        )
    ]


def test_sensitive_value_stops_at_control_character():
    assert _escape_for_log(_mask_sensitive("token=abcdef\nnext")) == r"token=a******\nnext"


def test_logger_configuration_is_idempotent():
    runtime_logger = _RecordingLogger()

    configured = _configure_logger(runtime_logger)
    first_method = configured.info
    configured_again = _configure_logger(runtime_logger)
    configured_again.info("token=abcdef")

    assert configured_again is configured
    assert configured_again.info is first_method
    assert configured.depth == 3
    assert configured.calls[-1][1] == "token=a******"


def test_log_level_monitor_loads_initial_value_and_stops(tmp_path):
    config = tmp_path / "runtime.ini"
    config.write_text("[log]\nlevel = DEBUG\n", encoding="utf-8")
    levels = []
    monitor = LogLevelMonitor(
        config_file_path=str(config),
        interval_seconds=0.01,
        level_setter=levels.append,
    )

    monitor.start()
    deadline = time.time() + 1
    while not monitor.is_running and time.time() < deadline:
        time.sleep(0.001)
    monitor.stop()

    assert levels == ["DEBUG"]
    assert monitor.is_running is False


def test_log_level_monitor_applies_file_changes_once(tmp_path):
    config = tmp_path / "runtime.ini"
    config.write_text("[log]\nlevel = INFO\n", encoding="utf-8")
    levels = []
    monitor = LogLevelMonitor(
        config_file_path=str(config),
        interval_seconds=0.01,
        level_setter=levels.append,
    )
    monitor.start()
    time.sleep(0.02)
    config.write_text("[log]\nlevel = ERROR\n", encoding="utf-8")
    deadline = time.time() + 1
    while levels != ["INFO", "ERROR"] and time.time() < deadline:
        time.sleep(0.01)
    monitor.stop()

    assert levels == ["INFO", "ERROR"]


def test_log_level_monitor_without_runtime_file_remains_stopped(monkeypatch):
    monkeypatch.delenv("PY_RUNTIME_FILE", raising=False)
    monitor = LogLevelMonitor(interval_seconds=0.01)

    monitor.start()

    assert monitor.is_running is False


def test_chatbi_server_owns_log_monitor_lifecycle(monkeypatch):
    from src.infrastructure import chatbi_server as server_module

    calls = []
    monkeypatch.setattr(server_module, "init_db", lambda: calls.append("db"))
    monkeypatch.setattr(server_module, "initialize_config_center", lambda: calls.append("config"))
    monkeypatch.setattr(server_module, "start_platform_runtime", lambda: calls.append("platform_start"))
    monkeypatch.setattr(server_module, "stop_platform_runtime", lambda: calls.append("platform_stop"))
    monkeypatch.setattr(server_module, "start_log_level_monitor", lambda: calls.append("log_start"))
    monkeypatch.setattr(server_module, "stop_log_level_monitor", lambda: calls.append("log_stop"))
    monkeypatch.setattr(server_module, "build_policy_auth_gateway", lambda: object())
    server = server_module.ChatBIServer()

    server.initialize()
    server.initialize()
    server.destroy()

    assert calls == ["db", "log_start", "config", "platform_start", "platform_stop", "log_stop"]
