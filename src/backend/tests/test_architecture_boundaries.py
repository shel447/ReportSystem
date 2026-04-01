import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = ROOT / "routers"
TARGET_ROUTERS = {"chat.py", "instances.py", "tasks.py", "templates.py", "documents.py"}
CONVERSATION_APPLICATION = ROOT / "contexts" / "conversation" / "application" / "services.py"
DEPENDENCY_BUILDER = ROOT / "infrastructure" / "dependencies.py"
TEMPLATE_CATALOG_REPOSITORY = ROOT / "contexts" / "template_catalog" / "infrastructure" / "repositories.py"
CONVERSATION_GATEWAYS = ROOT / "contexts" / "conversation" / "infrastructure" / "gateways.py"
SYSTEM_SETTINGS_ROUTER = ROUTERS_DIR / "system_settings.py"
REPORT_RUNTIME_GATEWAYS = ROOT / "contexts" / "report_runtime" / "infrastructure" / "gateways.py"
REPORTING_REPOSITORIES = ROOT / "infrastructure" / "reporting" / "repositories.py"
REPORTING_APPLICATION = ROOT / "application" / "reporting" / "services.py"
TEMPLATE_INSTANCES_ROUTER = ROUTERS_DIR / "template_instances.py"
CONVERSATION_STATE = ROOT / "contexts" / "conversation" / "infrastructure" / "state.py"
CONVERSATION_FLOW = ROOT / "contexts" / "conversation" / "infrastructure" / "flow.py"
CONVERSATION_FORKS = ROOT / "contexts" / "conversation" / "infrastructure" / "forks.py"

FORBIDDEN_ROUTER_MODULES = {
    "backend.models",
    "backend.ai_gateway",
    "backend.document_service",
    "backend.outline_review_service",
    "backend.report_generation_service",
    "backend.template_instance_service",
    "backend.chat_capability_service",
    "backend.chat_flow_service",
    "backend.chat_fork_service",
    "backend.chat_session_service",
    "backend.context_state_service",
}
FORBIDDEN_LAYER_IMPORT_SEGMENTS = {"fastapi", "sqlalchemy", "pydantic", "openai"}
CHECK_LAYERS = [ROOT / "contexts"]
FORBIDDEN_CONVERSATION_APPLICATION_MODULES = {
    "backend.ai_gateway",
    "backend.models",
    "backend.infrastructure.dependencies",
    "backend.chat_capability_service",
    "backend.chat_flow_service",
    "backend.chat_fork_service",
    "backend.chat_response_service",
    "backend.chat_session_service",
    "backend.context_state_service",
    "backend.document_service",
    "backend.outline_review_service",
    "backend.param_dialog_service",
    "backend.system_settings_service",
    "backend.template_instance_service",
    "backend.template_index_service",
}
FORBIDDEN_CHAT_ROUTER_SHIM_NAMES = {
    "get_settings_payload",
    "match_templates",
    "extract_params_from_message",
    "build_instance_application_service",
    "create_markdown_document",
    "serialize_document",
    "handle_smart_query_turn",
    "handle_fault_diagnosis_turn",
    "_sync_conversation_compatibility_overrides",
}
FORBIDDEN_DEPENDENCY_BUILDER_MODULES = {
    "backend.ai_gateway",
    "backend.application.reporting.services",
    "backend.domain.reporting.services",
    "backend.infrastructure.reporting.repositories",
    "backend.contexts.report_runtime.infrastructure.adapters",
}
FORBIDDEN_TEMPLATE_CATALOG_LEGACY_MODULES = {
    "backend.template_index_service",
    "backend.template_schema_service",
}
FORBIDDEN_CONVERSATION_GATEWAY_LEGACY_MODULES = {
    "backend.chat_flow_service",
    "backend.chat_fork_service",
    "backend.chat_response_service",
    "backend.chat_session_service",
    "backend.context_state_service",
    "backend.param_dialog_service",
    "backend.chat_capability_service",
    "backend.document_service",
    "backend.outline_review_service",
    "backend.template_instance_service",
}
FORBIDDEN_REPORT_RUNTIME_LEGACY_MODULES = {
    "backend.document_service",
    "backend.report_generation_service",
    "backend.template_instance_service",
    "backend.outline_review_service",
    "backend.template_v2_renderer",
}


def _resolve_import_from(path: Path, module: str | None, level: int) -> str:
    package_parts = ["backend", *path.relative_to(ROOT).with_suffix("").parts]
    base_parts = package_parts[:-level] if level > 0 else package_parts
    if module:
        return ".".join(base_parts + module.split("."))
    return ".".join(base_parts)


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_routers_do_not_import_legacy_business_or_orm_modules(self):
        violations: list[str] = []
        for path in ROUTERS_DIR.glob("*.py"):
            if path.name not in TARGET_ROUTERS:
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

    def test_conversation_application_does_not_import_legacy_root_modules(self):
        violations: list[str] = []
        tree = ast.parse(CONVERSATION_APPLICATION.read_text(encoding="utf-8-sig"), filename=str(CONVERSATION_APPLICATION))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_CONVERSATION_APPLICATION_MODULES:
                        violations.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = _resolve_import_from(CONVERSATION_APPLICATION, node.module, node.level)
                if module in FORBIDDEN_CONVERSATION_APPLICATION_MODULES:
                    violations.append(f"from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_chat_router_does_not_expose_compatibility_shim_symbols(self):
        path = ROUTERS_DIR / "chat.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        violations: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in FORBIDDEN_CHAT_ROUTER_SHIM_NAMES:
                violations.append(f"function {node.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in FORBIDDEN_CHAT_ROUTER_SHIM_NAMES:
                        violations.append(f"assignment {target.id}")
        self.assertEqual([], violations, "\n".join(violations))

    def test_dependency_builder_does_not_import_legacy_reporting_modules(self):
        violations: list[str] = []
        tree = ast.parse(DEPENDENCY_BUILDER.read_text(encoding="utf-8-sig"), filename=str(DEPENDENCY_BUILDER))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_DEPENDENCY_BUILDER_MODULES:
                        violations.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = _resolve_import_from(DEPENDENCY_BUILDER, node.module, node.level)
                if module in FORBIDDEN_DEPENDENCY_BUILDER_MODULES:
                    violations.append(f"from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_template_catalog_and_related_entrypoints_do_not_import_root_template_services(self):
        violations: list[str] = []
        for path in (TEMPLATE_CATALOG_REPOSITORY, CONVERSATION_GATEWAYS, SYSTEM_SETTINGS_ROUTER):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_TEMPLATE_CATALOG_LEGACY_MODULES:
                            violations.append(f"{path.relative_to(ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = _resolve_import_from(path, node.module, node.level)
                    if module in FORBIDDEN_TEMPLATE_CATALOG_LEGACY_MODULES:
                        violations.append(f"{path.relative_to(ROOT)}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_conversation_gateway_does_not_import_root_conversation_helpers(self):
        violations: list[str] = []
        tree = ast.parse(CONVERSATION_GATEWAYS.read_text(encoding="utf-8-sig"), filename=str(CONVERSATION_GATEWAYS))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_CONVERSATION_GATEWAY_LEGACY_MODULES:
                        violations.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = _resolve_import_from(CONVERSATION_GATEWAYS, node.module, node.level)
                if module in FORBIDDEN_CONVERSATION_GATEWAY_LEGACY_MODULES:
                    violations.append(f"from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))

    def test_report_runtime_related_entrypoints_do_not_import_root_runtime_helpers(self):
        violations: list[str] = []
        for path in (
            REPORT_RUNTIME_GATEWAYS,
            REPORTING_REPOSITORIES,
            REPORTING_APPLICATION,
            TEMPLATE_INSTANCES_ROUTER,
            CONVERSATION_STATE,
            CONVERSATION_FLOW,
            CONVERSATION_FORKS,
        ):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in FORBIDDEN_REPORT_RUNTIME_LEGACY_MODULES:
                            violations.append(f"{path.relative_to(ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = _resolve_import_from(path, node.module, node.level)
                    if module in FORBIDDEN_REPORT_RUNTIME_LEGACY_MODULES:
                        violations.append(f"{path.relative_to(ROOT)}: from {module} import ...")
        self.assertEqual([], violations, "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
