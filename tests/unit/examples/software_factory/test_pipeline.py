#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for the fix loop edge cases in the software factory example pipeline.

These tests call the pipeline's raw `.entrypoint` function directly (the
undecorated Python function stored by `@pipeline`) instead of running it
through the real dynamic pipeline orchestration machinery. All steps used
by `software_factory` are monkeypatched with plain Python callables, so
these tests exercise only the loop control flow in
`examples/software_factory/pipeline.py`, not real sandbox/agent/server
interactions.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

_EXAMPLE_DIR = (
    Path(__file__).resolve().parents[4] / "examples" / "software_factory"
)
if str(_EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLE_DIR))

import pipeline as sf_pipeline  # noqa: E402
from models import PRRef, Review, ReviewVerdict, TestReport  # noqa: E402


class _Loaded:
    """Stand-in for a dynamic pipeline output future with a `.load()`."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def load(self) -> Any:
        return self._value


@pytest.fixture
def recorder() -> Dict[str, List[Optional[str]]]:
    return {
        "write_plan": [],
        "open_workspace": [],
        "implement": [],
        "run_tests": [],
        "review": [],
        "fix": [],
        "close_workspace": [],
        "deploy": [],
        "wait": [],
    }


@pytest.fixture
def patch_steps(monkeypatch, recorder):
    """Replace every step/`wait` call used by `software_factory` with a stub.

    Returns a dict of dicts the test can populate to control the
    `TestReport`/`ReviewVerdict` returned for a given step `id`.
    """
    test_reports: Dict[str, TestReport] = {}
    review_verdicts: Dict[str, ReviewVerdict] = {}
    wait_metadata: Dict[str, Any] = {}

    def _fake_write_plan(*, repo, issue, base_branch=None):
        recorder["write_plan"].append(None)
        return _Loaded("plan text")

    def _fake_open_workspace(*, repo, branch, plan, base_branch=None):
        recorder["open_workspace"].append(None)
        return "workspace-id", base_branch or "main"

    def _fake_implement(*, workspace, repo, branch, issue, plan, base_branch):
        recorder["implement"].append(None)
        return _Loaded(PRRef(url="https://example.com/pr/1", number=1))

    def _fake_run_tests(
        *, workspace, repo, branch, test_command=None, id=None
    ):
        recorder["run_tests"].append(id)
        report = test_reports.get(
            id, TestReport(passed=True, summary=f"summary-{id}")
        )
        return _Loaded(report)

    def _fake_review(
        *,
        workspace,
        repo,
        branch,
        issue,
        plan,
        tests,
        base_branch,
        id=None,
    ):
        recorder["review"].append(id)
        verdict = review_verdicts.get(
            id, ReviewVerdict(approved=False, comments=[])
        )
        return _Loaded(verdict)

    def _fake_fix(
        *,
        workspace,
        repo,
        branch,
        issue,
        tests,
        base_branch,
        verdict=None,
        id=None,
    ):
        recorder["fix"].append(id)
        return _Loaded(PRRef(url="https://example.com/pr/1", number=1))

    def _fake_close_workspace(*, workspace):
        recorder["close_workspace"].append(None)

    def _fake_deploy(*, pr, repo):
        recorder["deploy"].append(None)

    def _fake_wait(
        *,
        schema=None,
        type=None,
        timeout=None,
        poll_interval=None,
        question=None,
        metadata=None,
        after=None,
        name=None,
    ):
        recorder["wait"].append(name)
        if name == "plan_review":
            return Review(approved=True, feedback="")
        if name == "deploy_approval":
            wait_metadata["deploy_approval"] = metadata
            return False
        raise AssertionError(f"Unexpected wait() call: name={name!r}")

    monkeypatch.setattr(sf_pipeline, "write_plan", _fake_write_plan)
    monkeypatch.setattr(sf_pipeline, "open_workspace", _fake_open_workspace)
    monkeypatch.setattr(sf_pipeline, "implement", _fake_implement)
    monkeypatch.setattr(sf_pipeline, "run_tests", _fake_run_tests)
    monkeypatch.setattr(sf_pipeline, "review", _fake_review)
    monkeypatch.setattr(sf_pipeline, "fix", _fake_fix)
    monkeypatch.setattr(sf_pipeline, "close_workspace", _fake_close_workspace)
    monkeypatch.setattr(sf_pipeline, "deploy", _fake_deploy)
    monkeypatch.setattr(sf_pipeline, "wait", _fake_wait)

    return {
        "test_reports": test_reports,
        "review_verdicts": review_verdicts,
        "wait_metadata": wait_metadata,
    }


def _run(max_fix_iterations: int) -> None:
    sf_pipeline.software_factory.entrypoint(
        repo="zenml-io/zenml",
        issue="Some bug",
        target_branch="fix/some-bug",
        base_branch="develop",
        test_command="pytest",
        max_fix_iterations=max_fix_iterations,
    )


def test_zero_max_fix_iterations_raises(recorder, patch_steps) -> None:
    with pytest.raises(ValueError, match="max_fix_iterations"):
        _run(max_fix_iterations=0)

    assert recorder["write_plan"] == []


def test_negative_max_fix_iterations_raises(recorder, patch_steps) -> None:
    with pytest.raises(ValueError, match="max_fix_iterations"):
        _run(max_fix_iterations=-1)

    assert recorder["write_plan"] == []


def test_loop_exhausted_runs_final_tests(recorder, patch_steps) -> None:
    patch_steps["test_reports"]["run_tests_final"] = TestReport(
        passed=True, summary="final-report"
    )

    _run(max_fix_iterations=2)

    assert recorder["run_tests"] == [
        "run_tests_0",
        "run_tests_1",
        "run_tests_final",
    ]
    assert recorder["review"] == ["review_0", "review_1"]
    assert recorder["fix"] == ["fix_0", "fix_1"]
    assert recorder["wait"] == ["plan_review", "deploy_approval"]

    metadata = patch_steps["wait_metadata"]["deploy_approval"]
    assert metadata["tests"]["summary"] == "final-report"


def test_loop_breaks_on_first_approval(recorder, patch_steps) -> None:
    patch_steps["review_verdicts"]["review_0"] = ReviewVerdict(
        approved=True, comments=[]
    )

    _run(max_fix_iterations=3)

    assert recorder["run_tests"] == ["run_tests_0"]
    assert recorder["review"] == ["review_0"]
    assert recorder["fix"] == []
    assert recorder["wait"] == ["plan_review", "deploy_approval"]

    metadata = patch_steps["wait_metadata"]["deploy_approval"]
    assert metadata["tests"]["summary"] == "summary-run_tests_0"
    assert metadata["verdict"]["approved"] is True
