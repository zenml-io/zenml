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
"""Tests for the test/review/fix loop edge cases in the software factory
example pipeline (examples/software_factory/pipeline.py).

The pipeline needs a live sandbox, the `claude` CLI and a real GitHub
repo/token to run end to end, so these tests load the module directly from
the example directory and replace every sandbox/GitHub/agent helper it uses
with lightweight fakes, exercising only the pure Python control flow of the
`software_factory` dynamic pipeline body.
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import pytest

from zenml.client import Client

EXAMPLE_DIR = (
    Path(__file__).resolve().parents[4] / "examples" / "software_factory"
)
MODULE_NAME = "_software_factory_pipeline_under_test"


@pytest.fixture
def pipeline_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Load `examples/software_factory/pipeline.py` as an isolated module."""
    # The `github`/`claude` secrets referenced by `secrets=[...]` on the
    # steps only need to exist for step compilation to succeed; their
    # values are never read because every helper that would use them is
    # replaced with a fake.
    client = Client()
    for secret_name in ("github", "claude"):
        try:
            client.get_secret(secret_name)
        except KeyError:
            client.create_secret(name=secret_name, values={"token": "fake"})

    monkeypatch.syspath_prepend(str(EXAMPLE_DIR))
    spec = importlib.util.spec_from_file_location(
        MODULE_NAME, EXAMPLE_DIR / "pipeline.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(MODULE_NAME, None)
        sys.modules.pop("factory_utils", None)
        sys.modules.pop("models", None)


class FakeSession:
    """Stand-in for `zenml.sandboxes.SandboxSession`."""

    def __init__(self, id: str = "session") -> None:
        self.id = id

    def close(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        pass


class FakeSandbox:
    """Stand-in for `zenml.sandboxes.BaseSandbox`."""

    def create_session(self, destroy_on_exit: bool = False) -> FakeSession:
        return FakeSession()


class FakeOutput:
    """Stand-in for `zenml.sandboxes.SandboxOutput`."""

    def __init__(
        self, stdout: str = "", stderr: str = "", exit_code: int = 0
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code


def _make_fake_run_command(test_exit_code: int) -> Callable[..., FakeOutput]:
    """Fake `run_command` that only cares about the `run_tests` test command."""

    def fake_run_command(
        session: FakeSession,
        command: Any,
        cwd: Optional[str] = "repo",
        env: Optional[Dict[str, str]] = None,
        check: bool = True,
    ) -> FakeOutput:
        if command[:2] == ["bash", "-lc"]:
            return FakeOutput(stdout="test output", exit_code=test_exit_code)
        return FakeOutput(exit_code=0)

    return fake_run_command


def _make_fake_read_repo_file(review_approved: bool) -> Callable[..., str]:
    def fake_read_repo_file(session: FakeSession, path: str) -> str:
        if path.endswith("plan.md"):
            return "plan body"
        if path.endswith("summary.md"):
            return "summary body"
        if path.endswith("review.json"):
            return json.dumps({"approved": review_approved, "comments": []})
        raise AssertionError(f"unexpected read_repo_file path: {path}")

    return fake_read_repo_file


def _make_fake_wait(
    module: Any, captured_metadata: Dict[str, Any]
) -> Callable[..., Any]:
    def fake_wait(
        schema: Any = None,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        if name == "plan_review":
            return module.Review(approved=True, feedback="")
        if name == "deploy_approval":
            captured_metadata.update(metadata or {})
            return False
        raise AssertionError(f"unexpected wait condition: {name}")

    return fake_wait


def _install_fakes(
    module: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    test_exit_code: int,
    review_approved: bool,
    captured_metadata: Dict[str, Any],
) -> None:
    monkeypatch.setattr(module, "active_sandbox", lambda: FakeSandbox())
    monkeypatch.setattr(
        module, "attach_sandbox", lambda workspace: FakeSession(workspace)
    )
    monkeypatch.setattr(
        module,
        "attach_or_recreate",
        lambda workspace, repo, branch: FakeSession(workspace),
    )
    monkeypatch.setattr(module, "branch_exists", lambda session, branch: False)
    monkeypatch.setattr(
        module, "clone_repo", lambda session, repo, ref=None: None
    )
    monkeypatch.setattr(module, "commit_all", lambda session, message: True)
    monkeypatch.setattr(module, "github_token", lambda: "fake-token")
    monkeypatch.setattr(
        module,
        "open_pr",
        lambda session, repo, branch, base, title, body: module.PRRef(
            url="https://github.com/example/repo/pull/1", number=1
        ),
    )
    monkeypatch.setattr(
        module, "plan_path", lambda branch: f"spec/plans/{branch}.md"
    )
    monkeypatch.setattr(module, "pr_body", lambda summary, branch, run: "body")
    monkeypatch.setattr(module, "push_branch", lambda session, branch: None)
    monkeypatch.setattr(
        module, "read_repo_file", _make_fake_read_repo_file(review_approved)
    )
    monkeypatch.setattr(
        module,
        "resolve_base_branch",
        lambda session, repo, base_branch: base_branch or "main",
    )
    monkeypatch.setattr(
        module, "run_agent", lambda session, prompt, cwd="repo": "ok"
    )
    monkeypatch.setattr(
        module, "run_command", _make_fake_run_command(test_exit_code)
    )
    monkeypatch.setattr(module, "run_url", lambda: None)
    monkeypatch.setattr(
        module, "write_repo_file", lambda session, path, content: None
    )
    monkeypatch.setattr(
        module, "wait", _make_fake_wait(module, captured_metadata)
    )


def test_zero_max_fix_iterations_raises(pipeline_module: Any) -> None:
    """`max_fix_iterations=0` must fail fast, before any step runs."""
    with pytest.raises(ValueError, match="max_fix_iterations"):
        pipeline_module.software_factory(
            repo="example/repo",
            issue="Some issue",
            target_branch="fix-branch",
            max_fix_iterations=0,
        )


def test_loop_exhausted_on_fix_reruns_tests(
    pipeline_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If every attempt ends in `fix`, the tests are re-run once more."""
    captured_metadata: Dict[str, Any] = {}
    _install_fakes(
        pipeline_module,
        monkeypatch,
        test_exit_code=1,
        review_approved=False,
        captured_metadata=captured_metadata,
    )

    run = pipeline_module.software_factory(
        repo="example/repo",
        issue="Some issue",
        target_branch="fix-branch",
        test_command="pytest",
        max_fix_iterations=2,
    )

    assert "run_tests_final" in run.steps
    # `open_workspace` is an explicit data dependency (the `workspace` param);
    # `fix_1` is the implicit dependency on the last synchronous step call.
    assert sorted(run.steps["run_tests_final"].spec.upstream_steps) == [
        "fix_1",
        "open_workspace",
    ]
    assert "fix_0" in run.steps
    assert "fix_1" in run.steps
    assert "review_0" not in run.steps
    assert "review_1" not in run.steps

    assert captured_metadata["tests"]["passed"] is False
    assert "verdict" not in captured_metadata


def test_loop_breaks_early_on_approval(
    pipeline_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An approved review on the first attempt stops the loop via `break`."""
    captured_metadata: Dict[str, Any] = {}
    _install_fakes(
        pipeline_module,
        monkeypatch,
        test_exit_code=0,
        review_approved=True,
        captured_metadata=captured_metadata,
    )

    run = pipeline_module.software_factory(
        repo="example/repo",
        issue="Some issue",
        target_branch="fix-branch",
        test_command="pytest",
        max_fix_iterations=2,
    )

    assert "run_tests_0" in run.steps
    assert "review_0" in run.steps
    assert "fix_0" not in run.steps
    assert "run_tests_1" not in run.steps
    assert "run_tests_final" not in run.steps

    assert captured_metadata["tests"]["passed"] is True
    assert captured_metadata["verdict"]["approved"] is True
