import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = ROOT / "routers"
TARGET_ROUTERS = {"chat.py", "instances.py", "tasks.py", "templates.py", "documents.py"}
CONVERSATION_APPLICATION = ROOT / "contexts" / "conversation" / "application" / "services.py"

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


if __name__ == "__main__":
    unittest.main()
