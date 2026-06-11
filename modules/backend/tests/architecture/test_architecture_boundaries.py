import ast
import unittest
from pathlib import Path

from runtime.server import ROUTE_ATTR

from src import register_handler
from src.shared.kernel.authenticated import get_authenticated_metadata

MODULE_ROOT = Path(__file__).resolve().parents[2]
ROOT = MODULE_ROOT / "src"
CONTROLLERS_DIR = ROOT / "controllers"
TARGET_CONTROLLERS = {"chat.py", "template.py", "report.py"}
FORBIDDEN_ROUTER_MODULES = {
    "src.models",
    "src.chat_flow_service",
    "src.chat_fork_service",
    "src.chat_session_service",
    "src.context_state_service",
    "src.outline_review_service",
    "src.report_generation_service",
    "src.template_index_service",
    "src.template_schema_service",
    "src.template_instance_service",
}
FORBIDDEN_LAYER_IMPORT_SEGMENTS = {"fastapi", "sqlalchemy", "pydantic", "openai"}
CHECK_LAYERS = [ROOT / "contexts"]
BUSINESS_CONTEXTS = {"conversation", "report", "data_analysis"}
ALLOWED_BACKEND_ROOT_FILES = {
    "__init__.py",
    "main.py",
}


def _resolve_import_from(path: Path, module: str | None, level: int) -> str:
    package_parts = ["backend", *path.relative_to(ROOT).with_suffix("").parts]
    base_parts = package_parts[:-level] if level > 0 else package_parts
    if module:
        return ".".join(base_parts + module.split("."))
    return ".".join(base_parts)


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_controllers_do_not_import_legacy_business_or_orm_modules(self):
        violations: list[str] = []
        for path in CONTROLLERS_DIR.glob("*.py"):
            if path.name not in TARGET_CONTROLLERS:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_ROUTER_MODULES:
                            violations.append(f"{path.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = _resolve_import_from(path, node.module, node.level)
                    if module in FORBIDDEN_ROUTER_MODULES:
                        violations.append(f"{path.name}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_domain_and_application_do_not_depend_on_web_or_orm_frameworks(self):
        violations: list[str] = []
        for root in CHECK_LAYERS:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if not any(segment in {"domain", "application"} for segment in path.parts):
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top = alias.name.split(".", 1)[0]
                            if top in FORBIDDEN_LAYER_IMPORT_SEGMENTS:
                                violations.append(f"{path.relative_to(ROOT)}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if module.startswith("."):
                            continue
                        top = module.split(".", 1)[0]
                        if top in FORBIDDEN_LAYER_IMPORT_SEGMENTS:
                            violations.append(f"{path.relative_to(ROOT)}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_root_has_no_legacy_application_or_domain_directories(self):
        violations = [name for name in ("application", "domain") if (ROOT / name).exists()]
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_root_contains_only_entry_files(self):
        violations: list[str] = []
        for path in ROOT.glob("*.py"):
            if path.name not in ALLOWED_BACKEND_ROOT_FILES:
                violations.append(str(path.relative_to(ROOT)))
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_root_contains_no_local_json_schema_mirrors(self):
        violations = [str(path.relative_to(ROOT)) for path in ROOT.glob("*.json")]
        self.assertEqual([], violations, "\n".join(violations))

    def test_conversation_application_uses_report_application_boundary_only(self):
        violations: list[str] = []
        root = ROOT / "contexts" / "conversation"
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                module = _resolve_import_from(path, node.module, node.level)
                if module.startswith("backend.contexts.report."):
                    violations.append(f"{path.relative_to(ROOT)}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_context_applications_do_not_depend_on_infrastructure(self):
        violations: list[str] = []
        for path in (ROOT / "contexts").glob("*/application/*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if ".infrastructure" in alias.name or alias.name.endswith("infrastructure"):
                            violations.append(f"{path.relative_to(ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = _resolve_import_from(path, node.module, node.level)
                    if ".infrastructure" in module or module.endswith("infrastructure"):
                        violations.append(f"{path.relative_to(ROOT)}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_business_context_applications_do_not_import_other_contexts(self):
        violations: list[str] = []
        for context in BUSINESS_CONTEXTS:
            root = ROOT / "contexts" / context / "application"
            for path in root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                for node in ast.walk(tree):
                    modules: list[str] = []
                    if isinstance(node, ast.Import):
                        modules.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        modules.append(_resolve_import_from(path, node.module, node.level))
                    for module in modules:
                        for other in BUSINESS_CONTEXTS - {context}:
                            if module.startswith(f"backend.contexts.{other}.") or module.startswith(f"src.contexts.{other}."):
                                violations.append(f"{path.relative_to(ROOT)}: {module}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_global_infrastructure_scenario_adapters_do_not_exist(self):
        path = ROOT / "infrastructure" / "scenarios"
        violations = [str(item.relative_to(ROOT)) for item in path.rglob("*.py")] if path.exists() else []
        self.assertEqual([], violations, "\n".join(violations))

    def test_business_scenario_registration_uses_neutral_names(self):
        violations: list[str] = []
        for context in BUSINESS_CONTEXTS - {"conversation"}:
            root = ROOT / "contexts" / context / "infrastructure"
            for path in root.rglob("*.py"):
                relative = str(path.relative_to(ROOT))
                if path.name in {"conversation.py", "chat.py"}:
                    violations.append(relative)
                source = path.read_text(encoding="utf-8-sig")
                if "ConversationScenario" in source or "ChatScenario" in source:
                    violations.append(f"{relative}: class or symbol contains ConversationScenario/ChatScenario")
        self.assertEqual([], violations, "\n".join(violations))

    def test_global_dependency_builder_only_collects_context_composition_builders(self):
        path = ROOT / "infrastructure" / "dependencies.py"
        violations: list[str] = []
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_import_from(path, node.module, node.level)
            if ".application" in module or ".domain" in module:
                violations.append(f"from {module} import ...")
            if ".contexts." in module and ".infrastructure.composition" not in module:
                violations.append(f"from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_context_infrastructure_does_not_import_other_context_application_or_domain(self):
        allowed = {
            "contexts/report/infrastructure/scenario_registration.py": (
                "backend.contexts.conversation.application.scenarios",
                "backend.contexts.conversation.domain.models",
            ),
            "contexts/data_analysis/infrastructure/scenario_registration.py": (
                "backend.contexts.conversation.application.scenarios",
                "backend.contexts.conversation.domain.models",
            ),
        }
        violations: list[str] = []
        for context in BUSINESS_CONTEXTS:
            root = ROOT / "contexts" / context / "infrastructure"
            for path in root.rglob("*.py"):
                relative = str(path.relative_to(ROOT))
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                for node in ast.walk(tree):
                    modules: list[str] = []
                    if isinstance(node, ast.Import):
                        modules.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        modules.append(_resolve_import_from(path, node.module, node.level))
                    for module in modules:
                        for other in BUSINESS_CONTEXTS - {context}:
                            if not (
                                module.startswith(f"backend.contexts.{other}.application")
                                or module.startswith(f"backend.contexts.{other}.domain")
                                or module.startswith(f"src.contexts.{other}.application")
                                or module.startswith(f"src.contexts.{other}.domain")
                            ):
                                continue
                            if any(module.startswith(prefix) for prefix in allowed.get(relative, ())):
                                continue
                            violations.append(f"{relative}: {module}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_report_dsl_compiler_has_no_infrastructure_dependencies(self):
        path = ROOT / "contexts" / "report" / "domain" / "report_dsl_compiler.py"
        source = path.read_text(encoding="utf-8-sig")
        for forbidden in ("infrastructure", "httpx", "jsonschema", "sqlite3"):
            self.assertNotIn(forbidden, source)

    def test_agentflow_does_not_own_conversation_or_chat_fields(self):
        root = ROOT / "shared" / "agentflow"
        source = "\n".join(path.read_text(encoding="utf-8-sig") for path in root.glob("*.py"))
        for forbidden in ("conversation_id", "chat_id", "conversationId", "chatId"):
            self.assertNotIn(forbidden, source)

    def test_legacy_event_dispatch_centers_do_not_exist(self):
        source = "\n".join(path.read_text(encoding="utf-8-sig") for path in ROOT.rglob("*.py"))
        for forbidden in ("class MetricsCenter", "class AsyncAuditDispatcher"):
            self.assertNotIn(forbidden, source)

    def test_config_center_contains_only_chatbi_business_configuration(self):
        root = ROOT / "shared" / "configuration"
        source = "\n".join(path.read_text(encoding="utf-8-sig") for path in root.glob("*.py"))
        for forbidden in (
            "ReportConfiguration",
            "DocumentConfiguration",
            "externalServices",
            "agentcore",
            "guardrail",
            "onequery",
            "base_url_by_service",
        ):
            self.assertNotIn(forbidden, source)

    def test_backend_does_not_own_platform_service_address_resolution(self):
        source = "\n".join(path.read_text(encoding="utf-8-sig") for path in ROOT.rglob("*.py"))
        for forbidden in (
            "PlatformHttpClient",
            "ExternalServiceConfig",
            "build_platform_client",
            "_service_base_url",
            "REPORT_EXTERNAL_BUSINESS_BASE_URL",
            "REPORT_EXTERNAL_TIMEOUT_SECONDS",
            "REPORT_PLATFORM_AUTHORIZATION",
        ):
            self.assertNotIn(forbidden, source)

    def test_business_contexts_do_not_read_configuration_sources_directly(self):
        violations: list[str] = []
        for path in (ROOT / "contexts").rglob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            for forbidden in ("os.getenv", "os.environ", "runtime.config", "SystemSetting"):
                if forbidden in source:
                    violations.append(f"{path.relative_to(ROOT)}: {forbidden}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_report_generation_service_does_not_own_document_dependencies(self):
        path = ROOT / "contexts" / "report" / "application" / "generation_service.py"
        source = path.read_text(encoding="utf-8-sig")
        for forbidden in ("document_repository", "export_job_repository", "document_gateway"):
            self.assertNotIn(forbidden, source)

    def test_report_controllers_do_not_manage_database_sessions(self):
        violations: list[str] = []
        for name in ("template.py", "report.py"):
            path = CONTROLLERS_DIR / name
            source = path.read_text(encoding="utf-8-sig")
            for forbidden in ("get_db", "get_dev_db", "Session", "sqlalchemy", "build_report_service"):
                if forbidden in source:
                    violations.append(f"{name}: references {forbidden}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_every_public_business_route_declares_policy_auth_metadata(self):
        violations: list[str] = []
        for controller in register_handler():
            self.assertEqual((object,), controller.__class__.__bases__)
            if controller.__class__.__name__ == "HealthCheckController":
                continue
            for name in dir(controller):
                endpoint = getattr(controller, name)
                route = getattr(endpoint, ROUTE_ATTR, None)
                if route is not None and get_authenticated_metadata(endpoint) is None:
                    violations.append(f"{route.method} {route.path}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_controllers_use_query_parameters_instead_of_path_parameters(self):
        violations: list[str] = []
        for controller in register_handler():
            for name in dir(controller):
                endpoint = getattr(controller, name)
                route = getattr(endpoint, ROUTE_ATTR, None)
                if route is not None and ("{" in route.path or "}" in route.path):
                    violations.append(f"{route.method} {route.path}")
        for path in CONTROLLERS_DIR.glob("*.py"):
            if "req.path_params" in path.read_text(encoding="utf-8-sig"):
                violations.append(f"{path.name}: references req.path_params")
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_only_controllers_import_tornado_request_handler(self):
        violations = []
        for path in ROOT.rglob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            for line in source.splitlines():
                if "tornado" not in line or line.strip().startswith("#"):
                    continue
                if CONTROLLERS_DIR in path.parents and line.strip() == "from tornado.web import RequestHandler":
                    continue
                violations.append(f"{path.relative_to(ROOT)}: {line.strip()}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_backend_does_not_assemble_tornado_server(self):
        violations = []
        for path in ROOT.rglob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            for forbidden in ("httpserver.HTTPServer", "ioloop.IOLoop", "web.Application("):
                if forbidden in source:
                    violations.append(f"{path.relative_to(ROOT)}: {forbidden}")
        self.assertEqual([], violations, "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
