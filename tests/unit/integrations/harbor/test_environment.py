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
import contextvars
import threading
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
    SandboxProvenance,
    ZenMLSandboxEnvironment,
    session_provenance_scope,
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
    # Instance state harbor's BaseEnvironment.__init__ sets and its exec
    # helpers (_merge_env) read; the fixture bypasses __init__, so it
    # must provide them itself.
    env._exec_env_overlays = contextvars.ContextVar(
        "exec_env_overlays", default=()
    )
    env._output_callbacks = contextvars.ContextVar(
        "output_callbacks", default=()
    )
    return env


def _patch_active_sandbox(monkeypatch: pytest.MonkeyPatch, sandbox) -> None:
    """Point the bridge's Client at a stack with the given sandbox."""
    monkeypatch.setattr(
        "zenml.integrations.harbor.environment.Client",
        lambda: SimpleNamespace(active_stack=SimpleNamespace(sandbox=sandbox)),
    )


def _modal_sandbox(session: _FakeSession) -> SimpleNamespace:
    """Fake Modal-flavored sandbox that hands out the given session."""
    return SimpleNamespace(
        flavor="modal", create_session=lambda settings=None: session
    )


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


def test_settings_override_rejects_flavor_without_image_knob() -> None:
    """A pinned docker_image on a flavor without an image knob is refused."""
    env = _bridge(_FakeSession(), docker_image="python:3.11-slim")
    sandbox = SimpleNamespace(
        flavor="local", image_settings=lambda image: None
    )
    with pytest.raises(NotImplementedError, match="image"):
        env._settings_override(sandbox)


def test_settings_override_uses_flavor_image_settings() -> None:
    """A pinned docker_image is translated via the flavor's capability."""
    env = _bridge(_FakeSession(), docker_image="python:3.11-slim")
    marker = SimpleNamespace(image="python:3.11-slim")
    sandbox = SimpleNamespace(
        flavor="kubernetes", image_settings=lambda image: marker
    )
    assert env._settings_override(sandbox) is marker


def test_network_isolation_rejected_by_harbor_validation() -> None:
    """Isolation-requiring policies are rejected at construction.

    The bridge declares no network isolation capabilities, so harbor's
    own capability validation refuses no-network/allowlist policies —
    the bridge no longer needs (or has) its own check.
    """
    from harbor.models.task.config import NetworkMode, NetworkPolicy

    env = _bridge(_FakeSession())
    with pytest.raises(ValueError, match="no-network"):
        env.validate_network_policy_support(
            NetworkPolicy(network_mode=NetworkMode.NO_NETWORK)
        )
    with pytest.raises(ValueError, match="allowlist"):
        env.validate_network_policy_support(
            NetworkPolicy(network_mode=NetworkMode.ALLOWLIST)
        )
    # The default public policy passes.
    env.validate_network_policy_support(
        NetworkPolicy(network_mode=NetworkMode.PUBLIC)
    )


def test_start_requires_sandbox_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stack without a Sandbox component fails with guidance."""
    env = _bridge(_FakeSession())
    _patch_active_sandbox(monkeypatch, None)
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.start(force_build=False))


def test_start_records_session_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A started session leaves the sandbox facts in the ambient scope."""
    session = _FakeSession()
    env = _bridge(session=None)
    _patch_active_sandbox(monkeypatch, _modal_sandbox(session))
    with session_provenance_scope() as registry:
        asyncio.run(env.start(force_build=False))
    provenance = registry["hello__test123"]
    assert provenance.flavor == "modal"
    # No task docker_image override was pinned.
    assert provenance.docker_image is None


def test_start_without_scope_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outside a scope (e.g. plain `harbor run`), nothing is recorded."""
    env = _bridge(session=None)
    _patch_active_sandbox(monkeypatch, _modal_sandbox(_FakeSession()))
    asyncio.run(env.start(force_build=False))
    with session_provenance_scope() as registry:
        assert registry == {}


def test_provenance_scopes_isolate_concurrent_threads() -> None:
    """Concurrent shard threads never see each other's sessions.

    Dynamic mapped steps run as threads in one process; a shared
    registry would let one shard observe or reset another's entries.
    """
    results = {}
    barrier = threading.Barrier(2)

    def _shard(name: str) -> None:
        with session_provenance_scope() as registry:
            barrier.wait(timeout=5)
            registry[name] = SandboxProvenance("modal", None)
            barrier.wait(timeout=5)
            results[name] = dict(registry)

    threads = [
        threading.Thread(target=_shard, args=(name,)) for name in ("a", "b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert results["a"] == {"a": SandboxProvenance("modal", None)}
    assert results["b"] == {"b": SandboxProvenance("modal", None)}


def test_cancelled_creation_reaps_abandoned_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session that finishes starting after cancellation is destroyed.

    Harbor's build/start timeout cancels start() while create_session
    keeps running in its worker thread; the resulting sandbox has no
    owner and must be reaped instead of leaking until provider TTL.
    """
    session = _FakeSession()
    creation_started = threading.Event()
    release_creation = threading.Event()

    def _slow_create(settings=None):
        creation_started.set()
        release_creation.wait(timeout=5)
        return session

    env = _bridge(session=None)
    _patch_active_sandbox(
        monkeypatch,
        SimpleNamespace(flavor="modal", create_session=_slow_create),
    )

    async def _cancel_mid_creation() -> None:
        task = asyncio.create_task(env.start(force_build=False))
        await asyncio.to_thread(creation_started.wait, 5)
        task.cancel()
        release_creation.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Let the reap callback scheduled on the loop run.
        for _ in range(10):
            if session.destroyed:
                break
            await asyncio.sleep(0.05)

    asyncio.run(_cancel_mid_creation())
    assert session.destroyed
    assert env._session is None


def test_exec_after_failed_start_carries_root_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harbor's post-failure cleanup errors point at the start failure."""
    env = _bridge(session=None)
    _patch_active_sandbox(monkeypatch, None)
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.start(force_build=False))
    # Harbor's cleanup calls exec() on the never-started env; the error
    # must surface the original failure, not a bare "before start()".
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.exec("cat /agent/logs"))


def test_failed_start_discards_prior_attempt_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed retry attempt must not inherit an earlier attempt's facts.

    Harbor retries reuse the trial name (== session id) with a fresh
    environment; if the retry fails before opening a sandbox, provenance
    recorded by the earlier attempt would misattribute an image to a
    trial that ran on no sandbox at all.
    """
    with session_provenance_scope() as registry:
        first_attempt = _bridge(session=None)
        _patch_active_sandbox(monkeypatch, _modal_sandbox(_FakeSession()))
        asyncio.run(first_attempt.start(force_build=False))
        assert "hello__test123" in registry

        retry_attempt = _bridge(session=None)
        _patch_active_sandbox(monkeypatch, None)
        with pytest.raises(RuntimeError, match="No Sandbox component"):
            asyncio.run(retry_attempt.start(force_build=False))
        assert registry == {}


def test_cancelled_start_records_root_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harbor's build timeout cancels start(); the cause must be kept.

    CancelledError is a BaseException, so a plain `except Exception`
    would leave the most common start-failure mode anonymous.
    """

    def _cancelled_create_session(settings=None):
        raise asyncio.CancelledError()

    env = _bridge(session=None)
    _patch_active_sandbox(
        monkeypatch,
        SimpleNamespace(
            flavor="modal", create_session=_cancelled_create_session
        ),
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(env.start(force_build=False))
    with pytest.raises(RuntimeError, match="cancelled"):
        asyncio.run(env.exec("true"))


def test_successful_restart_clears_stale_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recovered start() must not blame errors on the old failure."""
    env = _bridge(session=None)
    _patch_active_sandbox(monkeypatch, None)
    with pytest.raises(RuntimeError, match="No Sandbox component"):
        asyncio.run(env.start(force_build=False))

    _patch_active_sandbox(monkeypatch, _modal_sandbox(_FakeSession()))
    asyncio.run(env.start(force_build=False))
    asyncio.run(env.stop(delete=False))
    # After a successful start and a clean stop, a late call is a plain
    # "used after stop()" — not fallout of the long-recovered failure.
    with pytest.raises(RuntimeError, match="before start"):
        asyncio.run(env.exec("true"))


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
