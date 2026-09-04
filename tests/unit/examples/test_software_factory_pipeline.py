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
"""Unit tests for the fix loop control flow in the software factory example.

The pipeline module lives outside the `zenml` package (`examples/`) and is
only importable once its directory is on `sys.path`, mirroring how
`run.py` imports it. The pipeline's own steps talk to sandboxes and GitHub,
so these tests replace them with plain mocks and call the undecorated
`software_factory.entrypoint` directly to exercise the fix loop's control
flow in isolation.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import MagicMock

import pytest

EXAMPLE_DIR = (
    Path(__file__).resolve().parents[3] / "examples" / "software_factory"
)


@pytest.fixture
def software_factory_module() -> Iterator[SimpleNamespace]:
    """Import the example's `pipeline` module with its directory on path.

    Yields:
        The imported `pipeline` module.
    """
    sys.path.insert(0, str(EXAMPLE_DIR))
    for name in ("pipeline", "factory_utils", "models"):
        sys.modules.pop(name, None)
    try:
        import pipeline as pipeline_module

        yield pipeline_module
    finally:
        sys.path.remove(str(EXAMPLE_DIR))
        for name in ("pipeline", "factory_utils", "models"):
            sys.modules.pop(name, None)


def _dumpable(**fields: object) -> MagicMock:
    """Build a mock model-like object exposing `model_dump()` and `fields`.

    Args:
        fields: Attribute names and values to set on the mock, and to
            include in `model_dump()`'s return value.

    Returns:
        A mock object mimicking a Pydantic model.
    """
    obj = MagicMock()
    obj.model_dump.return_value = fields
    for name, value in fields.items():
        setattr(obj, name, value)
    return obj


def _artifact(value: object) -> MagicMock:
    """Build a mock step output whose `.load()` returns `value`.

    Args:
        value: The value `.load()` should return.

    Returns:
        A mock artifact.
    """
    artifact = MagicMock()
    artifact.load.return_value = value
    return artifact


def _patch_common_steps(monkeypatch: pytest.MonkeyPatch, module) -> MagicMock:  # type: ignore[no-untyped-def]
    """Patch the steps outside the fix loop with no-op mocks.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        module: The imported `pipeline` module.

    Returns:
        The mock used for `wait`, so tests can inspect its calls.
    """
    monkeypatch.setattr(
        module,
        "write_plan",
        MagicMock(return_value=_artifact("plan")),
    )

    def _wait_side_effect(**kwargs: object) -> object:
        if kwargs.get("name") == "deploy_approval":
            # Decline the deploy so the real `deploy` step is never invoked.
            return False
        return SimpleNamespace(approved=True)

    wait_mock = MagicMock(side_effect=_wait_side_effect)
    monkeypatch.setattr(module, "wait", wait_mock)
    monkeypatch.setattr(
        module,
        "open_workspace",
        MagicMock(return_value=("workspace", "main")),
    )
    monkeypatch.setattr(
        module,
        "implement",
        MagicMock(return_value=_artifact(_dumpable(url="pr-url"))),
    )
    monkeypatch.setattr(module, "close_workspace", MagicMock())
    monkeypatch.setattr(module, "deploy", MagicMock())
    return wait_mock


def test_zero_max_fix_iterations_raises_value_error(
    monkeypatch: pytest.MonkeyPatch, software_factory_module
) -> None:
    """`max_fix_iterations=0` raises a clear error instead of `NameError`."""
    module = software_factory_module
    _patch_common_steps(monkeypatch, module)
    run_tests_mock = MagicMock()
    monkeypatch.setattr(module, "run_tests", run_tests_mock)

    with pytest.raises(ValueError, match="max_fix_iterations"):
        module.software_factory.entrypoint(
            repo="owner/repo",
            issue="issue",
            target_branch="fix-branch",
            max_fix_iterations=0,
        )

    run_tests_mock.assert_not_called()


def test_exhausted_loop_reruns_tests_after_final_fix(
    monkeypatch: pytest.MonkeyPatch, software_factory_module
) -> None:
    """If the loop ends on a `fix`, tests are re-run for `deploy_approval`."""
    module = software_factory_module
    wait_mock = _patch_common_steps(monkeypatch, module)

    failing_report = _artifact(_dumpable(passed=False))
    final_report = _artifact(_dumpable(passed=True))
    run_tests_mock = MagicMock(side_effect=[failing_report, final_report])
    monkeypatch.setattr(module, "run_tests", run_tests_mock)
    monkeypatch.setattr(module, "review", MagicMock())
    monkeypatch.setattr(
        module,
        "fix",
        MagicMock(return_value=_artifact(_dumpable(url="pr-url"))),
    )

    module.software_factory.entrypoint(
        repo="owner/repo",
        issue="issue",
        target_branch="fix-branch",
        max_fix_iterations=1,
    )

    assert run_tests_mock.call_count == 2
    final_call_kwargs = run_tests_mock.call_args_list[-1].kwargs
    assert final_call_kwargs["id"] == "run_tests_final"

    deploy_approval_call = next(
        call
        for call in wait_mock.call_args_list
        if call.kwargs.get("name") == "deploy_approval"
    )
    assert (
        deploy_approval_call.kwargs["metadata"]["tests"]
        == final_report.load().model_dump()
    )


def test_approved_review_skips_final_rerun(
    monkeypatch: pytest.MonkeyPatch, software_factory_module
) -> None:
    """An approved review breaks the loop without an extra test run."""
    module = software_factory_module
    _patch_common_steps(monkeypatch, module)

    passing_report = _artifact(_dumpable(passed=True))
    run_tests_mock = MagicMock(return_value=passing_report)
    monkeypatch.setattr(module, "run_tests", run_tests_mock)
    monkeypatch.setattr(
        module,
        "review",
        MagicMock(return_value=_artifact(_dumpable(approved=True))),
    )
    fix_mock = MagicMock()
    monkeypatch.setattr(module, "fix", fix_mock)

    module.software_factory.entrypoint(
        repo="owner/repo",
        issue="issue",
        target_branch="fix-branch",
        max_fix_iterations=3,
    )

    assert run_tests_mock.call_count == 1
    fix_mock.assert_not_called()
