import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = ROOT / "routers"
TARGET_ROUTERS = {"chat.py", "templates.py", "reports.py", "parameter_options.py"}
FORBIDDEN_ROUTER_MODULES = {
    "backend.models",
    "backend.chat_flow_service",
    "backend.chat_fork_service",
    "backend.chat_session_service",
    "backend.context_state_service",
    "backend.outline_review_service",
    "backend.report_generation_service",
    "backend.template_index_service",
    "backend.template_schema_service",
    "backend.template_instance_service",
}
FORBIDDEN_LAYER_IMPORT_SEGMENTS = {"fastapi", "sqlalchemy", "pydantic", "openai"}
CHECK_LAYERS = [ROOT / "contexts"]
ALLOWED_BACKEND_ROOT_FILES = {
    "__init__.py",
    "main.py",
    "requirements.txt",
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


if __name__ == "__main__":
    unittest.main()
