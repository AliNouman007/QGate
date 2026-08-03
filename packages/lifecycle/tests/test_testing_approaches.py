"""Testing-approach metadata, QA strategy, and white-box adapter checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from suitest_lifecycle.config import Config, ServerConfig
from suitest_lifecycle.config import TestingConfig as LifecycleTestingConfig
from suitest_lifecycle.models import (
    CodeSummary,
    Mode,
    PlanCase,
    Priority,
)
from suitest_lifecycle.models import (
    TestingApproach as Approach,
)
from suitest_lifecycle.models import (
    TestLevel as Level,
)
from suitest_lifecycle.strategy import apply_strategy, resolve_approach
from suitest_lifecycle.whitebox import detect_adapter, execute, normalize_coverage


def _config(root: Path, *, approach: str = "auto") -> Config:
    return Config(
        mode=Mode.BACKEND,
        project_name="approach-demo",
        project_path=root,
        base_url="http://localhost:1",
        server=ServerConfig(autostart=False),
        testing=LifecycleTestingConfig(approach=approach),
        output_dir=root / "suitest-output",
    )


def test_auto_approach_uses_access_not_test_level(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.analysis_source = "repo"
    assert resolve_approach(config) is Approach.GRAY_BOX
    config.analysis_source = "openapi"
    assert resolve_approach(config) is Approach.BLACK_BOX
    config.testing.approach = "white-box"
    config.testing.level = Level.INTEGRATION
    assert resolve_approach(config) is Approach.WHITE_BOX


def test_strategy_annotates_existing_plan_without_new_output_tree(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cases = [
        PlanCase(
            id="TC001",
            title="health",
            description="health",
            category="API",
            priority=Priority.HIGH,
        )
    ]
    strategy = apply_strategy(
        config,
        CodeSummary(project_name="demo", mode=Mode.BACKEND),
        cases,
    )
    assert cases[0].testing_approach is Approach.GRAY_BOX
    assert cases[0].strategy_ref == "suitest_backend_test_strategy.json"
    assert strategy["qaChecks"]


def test_pytest_whitebox_execute_keeps_unified_suitest_output(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths=['tests']\n", encoding="utf-8"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_math.py").write_text(
        "def test_addition():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    config = _config(tmp_path, approach="white-box")
    config.testing.framework = "pytest"

    discovery = detect_adapter(tmp_path, "pytest").discover(tmp_path)
    assert discovery.capability == "suitest.whitebox.v1"
    assert discovery.targets == [tests / "test_math.py"]

    _summary, cases, run, paths = execute(config)
    assert run.passed == 1
    assert cases[0].framework == "pytest"
    assert paths.test_strategy_json.is_file()
    plan = json.loads(paths.test_plan_json.read_text(encoding="utf-8"))
    assert plan[0]["testingApproach"] == "WHITE_BOX"
    assert paths.mode_dir == tmp_path / "suitest-output" / "backend"
    assert not (tmp_path / "suitest-output" / "whitebox").exists()
    assert sys.executable in discovery.command


def test_normalize_pytest_and_istanbul_coverage(tmp_path: Path) -> None:
    pytest_json = tmp_path / "coverage.json"
    pytest_json.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 10,
                    "covered_lines": 8,
                    "percent_covered": 80,
                    "num_branches": 4,
                    "covered_branches": 3,
                }
            }
        ),
        encoding="utf-8",
    )
    normalized = normalize_coverage(pytest_json)
    assert normalized is not None
    assert normalized["lines"] == {"total": 10, "covered": 8, "percent": 80}

    istanbul_json = tmp_path / "coverage-final.json"
    istanbul_json.write_text(
        json.dumps(
            {
                "total": {
                    "lines": {"total": 20, "covered": 18, "pct": 90},
                    "branches": {"total": 10, "covered": 7, "pct": 70},
                }
            }
        ),
        encoding="utf-8",
    )
    normalized = normalize_coverage(istanbul_json)
    assert normalized is not None
    assert normalized["branches"] == {"total": 10, "covered": 7, "percent": 70}
