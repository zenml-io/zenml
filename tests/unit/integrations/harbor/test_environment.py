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
"""Tests for the Sandbox environment bridge (skipped without Harbor)."""

import asyncio
from types import SimpleNamespace

import pytest

# Skip on a concrete submodule: without harbor installed, the bare
# "harbor" import can still succeed as an accidental namespace
# package (e.g. this test directory itself on sys.path).
pytest.importorskip("harbor.job")

from harbor.models.task.config import (  # noqa: E402
    EnvironmentConfig as TaskEnvironmentConfig,
)

from zenml.integrations.harbor.environment import (  # noqa: E402
    ZenMLSandboxEnvironment,
    pop_session_provenance,
)


class _FakeProcess:
    def __init__(self, stdout="out", stderr="", exit_code=0):
        self._output = SimpleNamespace(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            stdout_truncated=False,
            stderr_truncated=False,
        )

    def collect(self):
        return self._output


class _FakeSession:
    def __init__(self):
        self.id = "sb-fake"
        self.exec_calls = []
        self.uploads = []
        self.closed = False
        self.destroyed = False

    def exec(self, argv, cwd=None, env=None):
        self.exec_calls.append({"argv": argv, "cwd": cwd, "env": env})
        return _FakeProcess()

    def upload_file(self, local_path, remote_path):
        self.uploads.append((local_path, remote_path))

    def close(self):
        self.closed = True

    def destroy(self):
        self.destroyed = True


def _bridge(
    session: _FakeSession = None, **env_config
) -> ZenMLSandboxEnvironment:
    """Build a bridge instance without running BaseEnvironment.__init__."""
    env = object.__new__(ZenMLSandboxEnvironment)
    env._session = session
    env._persistent_env = {"PERSISTENT": "1"}
    env.session_id = "hello__test123"
    env.task_env_config = TaskEnvironmentConfig(**env_config)
    return env


def test_exec_wraps_command_in_bash() -> None:
    """Commands run via `bash -c` with the merged environment."""
    session = _FakeSession()
    env = _bridge(session)
    result = asyncio.run(env.exec("echo hi > /tmp/x", env={"EXTRA": "2"}))
    assert result.return_code == 0
    call = session.exec_calls[0]
    assert call["argv"] == ["bash", "-c", "echo hi > /tmp/x"]
    assert call["env"] == {"PERSISTENT": "1", "EXTRA": "2"}


def test_exec_enforces_timeout_via_coreutils() -> None:
    """A timeout prepends coreutils `timeout` to the argv."""
    session = _FakeSession()
    env = _bridge(session)
    asyncio.run(env.exec("sleep 100", timeout_sec=5))
    assert session.exec_calls[0]["argv"] == [
        "timeout",
        "5",
        "bash",
        "-c",
        "sleep 100",
    ]


def test_exec_before_start_raises() -> None:
    """Using the bridge before start() fails clearly."""
    env = _bridge(session=None)
    with pytest.raises(RuntimeError, match="before start"):
        asyncio.run(env.exec("true"))


def test_settings_override_none_without_image() -> None:
    """No task docker_image means no settings override."""
    env = _bridge(_FakeSession())
    sandbox = SimpleNamespace(flavor="modal")
    assert env._settings_override(sandbox) is None


def test_settings_override_rejects_non_modal_flavor() -> None:
    """A pinned docker_image on a non-Modal flavor is refused."""
    env = _bridge(_FakeSession(), docker_image="python:3.11-slim")
    sandbox = SimpleNamespace(flavor="kubernetes")
    with pytest.raises(NotImplementedError, match="Modal"):
        env._settings_override(sandbox)


def test_start_refuses_network_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """allow_internet=false is refused rather than silently ignored."""
    env = _bridge(_FakeSession(), allow_internet=False)
    monkeypatch.setattr(
        "zenml.integrations.harbor.environment.Client",
        lambda: SimpleNamespace(
            active_stack=SimpleNamespace(
                sandbox=SimpleNamespace(flavor="modal")
            )
        ),
    )
    with pytest.raises(NotImplementedError, match="allow_internet"):
        asyncio.run(env.start(force_build=False))


def test_start_requires_sandbox_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stack without a Sandbox component fails with guidance."""
    env = _bridge(_FakeSession())
    monkeypatch.setattr(
        "zenml.integrations.harbor.environment.Client",
        lambda: SimpleNamespace(active_stack=SimpleNamespace(sandbox=None)),
    )
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.start(force_build=False))


def test_start_records_session_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A started session leaves the sandbox facts for the shard runner."""
    session = _FakeSession()
    env = _bridge(session=None)
    monkeypatch.setattr(
        "zenml.integrations.harbor.environment.Client",
        lambda: SimpleNamespace(
            active_stack=SimpleNamespace(
                sandbox=SimpleNamespace(
                    flavor="modal",
                    create_session=lambda settings=None: session,
                )
            )
        ),
    )
    asyncio.run(env.start(force_build=False))
    provenance = pop_session_provenance("hello__test123")
    assert provenance is not None
    assert provenance.flavor == "modal"
    # No task docker_image override was pinned.
    assert provenance.docker_image is None
    # Pop-on-read: a second lookup finds nothing.
    assert pop_session_provenance("hello__test123") is None


def test_exec_after_failed_start_carries_root_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harbor's post-failure cleanup errors point at the start failure."""
    env = _bridge(session=None)
    monkeypatch.setattr(
        "zenml.integrations.harbor.environment.Client",
        lambda: SimpleNamespace(active_stack=SimpleNamespace(sandbox=None)),
    )
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.start(force_build=False))
    # Harbor's cleanup calls exec() on the never-started env; the error
    # must surface the original failure, not a bare "before start()".
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.exec("cat /agent/logs"))


def test_stop_destroys_or_closes() -> None:
    """stop(delete=True) destroys; stop(delete=False) closes."""
    session = _FakeSession()
    env = _bridge(session)
    asyncio.run(env.stop(delete=True))
    assert session.destroyed and not session.closed
    assert env._session is None

    session = _FakeSession()
    env = _bridge(session)
    asyncio.run(env.stop(delete=False))
    assert session.closed and not session.destroyed


def test_upload_dir_tars_through_single_file(tmp_path) -> None:
    """Directory upload goes tar -> upload_file -> in-sandbox untar."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.txt").write_text("a")
    session = _FakeSession()
    env = _bridge(session)
    asyncio.run(env.upload_dir(tmp_path / "src", "/target dir"))
    assert len(session.uploads) == 1
    remote_tar = session.uploads[0][1]
    command = session.exec_calls[0]["argv"][-1]
    assert f"mkdir -p '/target dir' && tar xzf {remote_tar}" in command
    assert command.endswith(f"&& rm -f {remote_tar}")
