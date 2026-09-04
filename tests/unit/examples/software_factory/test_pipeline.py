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

The real steps of `examples/software_factory/pipeline.py` drive Claude Code
sandboxes and GitHub, so they aren't exercised here. Instead, the pipeline's
own step functions are monkeypatched with lightweight stand-ins and the
dynamic pipeline itself is run for real (against the local test stack) so
that the actual control flow of `software_factory` -- the bounded fix loop
and its edge cases -- is what's under test.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import pytest

import zenml
from zenml import step

EXAMPLE_DIR = Path(zenml.__file__).resolve().parents[2] / "examples" / "software_factory"


def _load_example_module(name: str, filename: str) -> Any:
    """Load a module from the software factory example by file path.

    The example's modules use plain top-level imports (e.g. `from models
    import ...`), so the example directory needs to be on `sys.path` for
    them to resolve, independent of the name used to load this module.
    """
    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))
    spec = importlib.util.spec_from_file_location(
        name, EXAMPLE_DIR / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


models = _load_example_module("_software_factory_models", "models.py")
sf_pipeline = _load_example_module("_software_factory_pipeline", "pipeline.py")

PRRef = models.PRRef
TestReport = models.TestReport
ReviewVerdict = models.ReviewVerdict


class _RecordingWait:
    """Stand-in for `zenml.wait()` that resolves immediately.

    Records every call so tests can assert on the metadata passed to the
    `deploy_approval` wait condition, and returns canned results keyed by
    the wait condition's `name` so the pipeline doesn't actually block.
    """

    def __init__(
        self,
        plan_review_approved: bool = True,
        deploy_approval_result: bool = False,
    ) -> None:
        self.plan_review_approved = plan_review_approved
        self.deploy_approval_result = deploy_approval_result
        self.calls: List[Dict[str, Any]] = []

    def __call__(
        self,
        schema: Any = None,
        type: Any = None,
        timeout: int = 600,
        poll_interval: int = 5,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        after: Any = None,
        name: Optional[str] = None,
    ) -> Any:
        self.calls.append({"name": name, "metadata": metadata})
        if name == "plan_review":
            return SimpleNamespace(approved=self.plan_review_approved)
        if name == "deploy_approval":
            return self.deploy_approval_result
        raise AssertionError(f"Unexpected wait() call with name={name!r}")


class _StepCallRecorder:
    """Tracks how many times each fake step was invoked in a test."""

    def __init__(self) -> None:
        self.run_tests_reports: List[TestReport] = []
        self.review_approved: bool = False
        self.run_tests_calls = 0
        self.review_calls = 0
        self.fix_calls = 0

    def next_test_report(self) -> TestReport:
        index = min(self.run_tests_calls, len(self.run_tests_reports) - 1)
        return self.run_tests_reports[index]


@pytest.fixture
def recorder() -> _StepCallRecorder:
    return _StepCallRecorder()


@pytest.fixture(autouse=True)
def patch_steps(
    monkeypatch: pytest.MonkeyPatch, recorder: _StepCallRecorder
) -> None:
    """Replace every real step with a lightweight fake.

    None of the fakes talk to sandboxes, GitHub or Claude -- they just
    exercise the dynamic pipeline's step-invocation and artifact-loading
    machinery so the loop logic in `software_factory` runs for real.
    """

    @step
    def fake_write_plan(
        repo: str, issue: str, base_branch: Optional[str] = None
    ) -> str:
        return "PLAN"

    @step
    def fake_open_workspace(
        repo: str,
        branch: str,
        plan: str,
        base_branch: Optional[str] = None,
    ) -> Tuple[str, str]:
        return "workspace-1", base_branch or "main"

    @step
    def fake_implement(
        workspace: str,
        repo: str,
        branch: str,
        issue: str,
        plan: str,
        base_branch: str,
    ) -> PRRef:
        return PRRef(url="https://example.com/pulls/1", number=1)

    @step
    def fake_run_tests(
        workspace: str,
        repo: str,
        branch: str,
        test_command: Optional[str] = None,
    ) -> TestReport:
        report = recorder.next_test_report()
        recorder.run_tests_calls += 1
        return report

    @step
    def fake_review(
        workspace: str,
        repo: str,
        branch: str,
        issue: str,
        plan: str,
        tests: TestReport,
        base_branch: str,
    ) -> ReviewVerdict:
        recorder.review_calls += 1
        return ReviewVerdict(approved=recorder.review_approved, comments=[])

    @step
    def fake_fix(
        workspace: str,
        repo: str,
        branch: str,
        issue: str,
        tests: TestReport,
        base_branch: str,
        verdict: Optional[ReviewVerdict] = None,
    ) -> PRRef:
        recorder.fix_calls += 1
        return PRRef(url="https://example.com/pulls/1", number=1)

    @step
    def fake_close_workspace(workspace: str) -> None:
        return None

    @step
    def fake_deploy(pr: PRRef, repo: str) -> None:
        return None

    monkeypatch.setattr(sf_pipeline, "write_plan", fake_write_plan)
    monkeypatch.setattr(sf_pipeline, "open_workspace", fake_open_workspace)
    monkeypatch.setattr(sf_pipeline, "implement", fake_implement)
    monkeypatch.setattr(sf_pipeline, "run_tests", fake_run_tests)
    monkeypatch.setattr(sf_pipeline, "review", fake_review)
    monkeypatch.setattr(sf_pipeline, "fix", fake_fix)
    monkeypatch.setattr(sf_pipeline, "close_workspace", fake_close_workspace)
    monkeypatch.setattr(sf_pipeline, "deploy", fake_deploy)


def test_zero_max_fix_iterations_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`max_fix_iterations=0` must fail fast instead of hitting a NameError."""
    fake_wait = _RecordingWait()
    monkeypatch.setattr(sf_pipeline, "wait", fake_wait)

    with pytest.raises(ValueError, match="max_fix_iterations"):
        sf_pipeline.software_factory(
            repo="owner/repo",
            issue="issue",
            target_branch="fix-branch",
            max_fix_iterations=0,
        )
    assert fake_wait.calls == []


def test_negative_max_fix_iterations_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative `max_fix_iterations` values are rejected too, not just 0."""
    fake_wait = _RecordingWait()
    monkeypatch.setattr(sf_pipeline, "wait", fake_wait)

    with pytest.raises(ValueError, match="max_fix_iterations"):
        sf_pipeline.software_factory(
            repo="owner/repo",
            issue="issue",
            target_branch="fix-branch",
            max_fix_iterations=-1,
        )
    assert fake_wait.calls == []


def test_loop_exhausted_after_fix_reruns_tests(
    monkeypatch: pytest.MonkeyPatch, recorder: _StepCallRecorder
) -> None:
    """If the loop runs out of attempts on a `fix`, tests run once more.

    Every review is rejected across all attempts, so the loop never
    breaks. The `else` branch of the `for` loop must run one final
    `run_tests` (with id `run_tests_final`) so the `deploy_approval`
    metadata reflects the branch state after the last fix.
    """
    recorder.run_tests_reports = [
        TestReport(passed=True, summary="ok"),
    ]
    recorder.review_approved = False
    fake_wait = _RecordingWait()
    monkeypatch.setattr(sf_pipeline, "wait", fake_wait)

    sf_pipeline.software_factory(
        repo="owner/repo",
        issue="issue",
        target_branch="fix-branch",
        max_fix_iterations=2,
    )

    assert recorder.run_tests_calls == 3
    assert recorder.review_calls == 2
    assert recorder.fix_calls == 2

    deploy_call = next(
        c for c in fake_wait.calls if c["name"] == "deploy_approval"
    )
    assert deploy_call["metadata"]["tests"] == TestReport(
        passed=True, summary="ok"
    ).model_dump()
    assert "verdict" in deploy_call["metadata"]


def test_loop_breaks_early_skips_final_rerun(
    monkeypatch: pytest.MonkeyPatch, recorder: _StepCallRecorder
) -> None:
    """When the review approves on the first attempt, no extra rerun happens."""
    recorder.run_tests_reports = [TestReport(passed=True, summary="ok")]
    recorder.review_approved = True
    fake_wait = _RecordingWait()
    monkeypatch.setattr(sf_pipeline, "wait", fake_wait)

    sf_pipeline.software_factory(
        repo="owner/repo",
        issue="issue",
        target_branch="fix-branch",
        max_fix_iterations=3,
    )

    assert recorder.run_tests_calls == 1
    assert recorder.review_calls == 1
    assert recorder.fix_calls == 0


def test_single_iteration_exhausted_via_fix_reruns_tests(
    monkeypatch: pytest.MonkeyPatch, recorder: _StepCallRecorder
) -> None:
    """Minimal regression case: one iteration, failing tests, then a fix.

    The single attempt's tests fail, so `fix` runs without ever reviewing.
    The loop then exhausts without a `break`, so tests must run again and
    the `deploy_approval` metadata must reflect that final, passing report
    instead of the stale failing one from the only loop iteration.
    """
    recorder.run_tests_reports = [
        TestReport(passed=False, summary="failing"),
        TestReport(passed=True, summary="fixed"),
    ]
    fake_wait = _RecordingWait()
    monkeypatch.setattr(sf_pipeline, "wait", fake_wait)

    sf_pipeline.software_factory(
        repo="owner/repo",
        issue="issue",
        target_branch="fix-branch",
        max_fix_iterations=1,
    )

    assert recorder.run_tests_calls == 2
    assert recorder.review_calls == 0
    assert recorder.fix_calls == 1

    deploy_call = next(
        c for c in fake_wait.calls if c["name"] == "deploy_approval"
    )
    assert deploy_call["metadata"]["tests"] == TestReport(
        passed=True, summary="fixed"
    ).model_dump()
