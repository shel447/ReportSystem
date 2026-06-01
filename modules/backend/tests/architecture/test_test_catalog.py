from __future__ import annotations

from pathlib import Path
import re

from src.shared.kernel.paths import runtime_data_dir

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parents[1]
TESTS_ROOT = BACKEND_ROOT / "tests"


def test_backend_tests_are_grouped_by_context_or_feature():
    flat_tests = sorted(path.name for path in TESTS_ROOT.glob("test_*.py"))
    assert flat_tests == []


def test_testing_documentation_and_shared_testdata_exist():
    expected = [
        PROJECT_ROOT / "docs" / "dev" / "testing" / "README.md",
        PROJECT_ROOT / "docs" / "dev" / "testing" / "backend-cases.md",
        PROJECT_ROOT / "docs" / "dev" / "testing" / "exporter-cases.md",
        PROJECT_ROOT / "docs" / "dev" / "testing" / "feature-e2e-cases.md",
        PROJECT_ROOT / "testdata" / "README.md",
        PROJECT_ROOT / "testdata" / "report-dsl" / "showcase-flow.json",
        PROJECT_ROOT / "testdata" / "report-dsl" / "showcase-paged.json",
    ]
    assert [str(path.relative_to(PROJECT_ROOT)) for path in expected if not path.exists()] == []


def test_runtime_and_test_directories_are_documented_as_separate_roots():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    testing_docs = (PROJECT_ROOT / "docs" / "dev" / "testing" / "README.md").read_text(encoding="utf-8")
    assert ".runtime/" in gitignore
    assert ".test/" in gitignore
    assert ".runtime/" in testing_docs
    assert ".test/" in testing_docs
    assert ".test" in runtime_data_dir().parts
    assert runtime_data_dir() != PROJECT_ROOT / ".runtime"


def test_backend_test_file_catalog_matches_source_tree():
    catalog = (PROJECT_ROOT / "docs" / "dev" / "testing" / "backend-cases.md").read_text(encoding="utf-8")
    documented = {
        item
        for item in re.findall(r"`(tests/[^`]+test_[^`]+\.py)`", catalog)
    }
    actual = {
        path.relative_to(BACKEND_ROOT).as_posix()
        for path in TESTS_ROOT.rglob("test_*.py")
    }
    assert documented == actual
