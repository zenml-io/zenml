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
"""Unit tests for the DockerSandbox flavor (docker SDK mocked)."""

import io
import tarfile
import threading
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest
from docker.errors import ImageNotFound, NotFound

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    DockerSandbox,
    DockerSandboxConfig,
    DockerSandboxFlavor,
    DockerSandboxPullPolicy,
    DockerSandboxSettings,
    SandboxSnapshot,
)
from zenml.sandboxes.docker_sandbox import DockerSandboxSession


class _FakeAPI:
    """Low-level docker API stub covering exec_create/start/inspect."""

    def __init__(
        self,
        chunks: Optional[List[Any]] = None,
        exit_code: int = 0,
        gate: Optional[threading.Event] = None,
    ):
        self.chunks = chunks or []
        self.exit_code = exit_code
        self.gate = gate
        self.exec_creates: List[Dict[str, Any]] = []
        self._running = True

    def exec_create(self, container_id, cmd, environment=None, workdir=None):
        self.exec_creates.append(
            {
                "container_id": container_id,
                "cmd": cmd,
                "environment": environment,
                "workdir": workdir,
            }
        )
        return {"Id": f"exec-{len(self.exec_creates)}"}

    def exec_start(self, exec_id, stream=False, demux=False):
        if not stream:
            return b""

        return self._stream()

    def _stream(self):
        yield from self.chunks
        if self.gate is not None:
            self.gate.wait(timeout=10)
        self._running = False

    def exec_inspect(self, exec_id):
        return {
            "Running": self._running,
            "ExitCode": None if self._running else self.exit_code,
        }


class _FakeContainer:
    """Container stub with archive round-trip support."""

    def __init__(self, api: _FakeAPI):
        self.id = "c-1"
        self.client = SimpleNamespace(api=api)
        self.archives: Dict[str, bytes] = {}
        self.removed = False
        self.committed = []

    def put_archive(self, directory, data):
        buffer = io.BytesIO(data)
        with tarfile.open(fileobj=buffer) as tar:
            for member in tar.getmembers():
                extracted = tar.extractfile(member)
                if extracted:
                    self.archives[f"{directory.rstrip('/')}/{member.name}"] = (
                        extracted.read()
                    )
        return True

    def get_archive(self, path):
        if path not in self.archives:
            raise NotFound(f"No such file: {path}")
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            payload = self.archives[path]
            info = tarfile.TarInfo(name=path.rsplit("/", 1)[-1])
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        buffer.seek(0)
        return iter([buffer.getvalue()]), {}

    def remove(self, force=False):
        self.removed = True

    def commit(self, repository, tag):
        self.committed.append((repository, tag))
        return SimpleNamespace(
            id="sha256:deadbeef", tags=[f"{repository}:{tag}"]
        )


class _FakeContainers:
    """Container collection stub."""

    def __init__(self, api: _FakeAPI):
        self.api = api
        self.run_calls: List[Dict[str, Any]] = []
        self.containers: List[_FakeContainer] = []

    def run(self, **kwargs):
        self.run_calls.append(kwargs)
        container = _FakeContainer(self.api)
        self.containers.append(container)
        return container

    def list(self, filters=None):
        label = filters["label"]
        return [
            container
            for call, container in zip(self.run_calls, self.containers)
            if f"zenml-sandbox-session={call['labels']['zenml-sandbox-session']}"
            == label
        ]


class _FakeImages:
    """Image collection stub."""

    def __init__(self, present: Optional[List[str]] = None):
        self.present = set(present or [])
        self.pulled: List[str] = []

    def get(self, image):
        if image not in self.present:
            raise ImageNotFound(f"No such image: {image}")

    def pull(self, image):
        self.pulled.append(image)
        self.present.add(image)


class _FakeClient:
    """Docker client stub."""

    def __init__(
        self,
        api: Optional[_FakeAPI] = None,
        present_images: Optional[List[str]] = None,
    ):
        self.api = api or _FakeAPI()
        self.containers = _FakeContainers(self.api)
        self.images = _FakeImages(present_images)


def _make_sandbox(
    client: Optional[_FakeClient] = None,
    config: Optional[DockerSandboxConfig] = None,
) -> DockerSandbox:
    """Builds a DockerSandbox with a fake docker client."""
    sandbox = DockerSandbox(
        name="test-docker",
        id=uuid4(),
        config=config or DockerSandboxConfig(),
        flavor="docker",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
    )
    sandbox._docker_engine = SimpleNamespace(client=client or _FakeClient())
    return sandbox


def _make_session(
    api: Optional[_FakeAPI] = None,
) -> DockerSandboxSession:
    """Builds a session backed by fakes through the sandbox."""
    client = _FakeClient(api=api, present_images=["python:3.11-slim"])
    session = _make_sandbox(client).create_session()
    assert isinstance(session, DockerSandboxSession)
    return session


def _wrapped_command(call: Dict[str, Any]) -> List[str]:
    """Strips the pid file wrapper from an exec_create call."""
    assert call["cmd"][:2] == ["sh", "-c"]
    return call["cmd"][5:]


class TestFlavor:
    def test_flavor_shape(self) -> None:
        flavor = DockerSandboxFlavor()
        assert flavor.name == "docker"
        assert flavor.implementation_class is DockerSandbox
        assert flavor.config_class().is_local is True

    def test_registered_as_builtin(self) -> None:
        from zenml.stack.flavor_registry import FlavorRegistry

        names = [flavor().name for flavor in FlavorRegistry().builtin_flavors]
        assert "docker" in names


class TestCreateSession:
    def test_pulls_missing_image(self) -> None:
        client = _FakeClient()
        _make_sandbox(client).create_session()
        assert client.images.pulled == ["python:3.11-slim"]

    def test_present_image_is_not_pulled(self) -> None:
        client = _FakeClient(present_images=["python:3.11-slim"])
        _make_sandbox(client).create_session()
        assert client.images.pulled == []

    def test_always_policy_pulls_present_image(self) -> None:
        client = _FakeClient(present_images=["python:3.11-slim"])
        sandbox = _make_sandbox(client)
        sandbox.create_session(
            settings=DockerSandboxSettings(
                pull_policy=DockerSandboxPullPolicy.ALWAYS
            )
        )
        assert client.images.pulled == ["python:3.11-slim"]

    def test_never_policy_raises_for_missing_image(self) -> None:
        sandbox = _make_sandbox(_FakeClient())
        with pytest.raises(RuntimeError, match="pull policy"):
            sandbox.create_session(
                settings=DockerSandboxSettings(
                    pull_policy=DockerSandboxPullPolicy.NEVER
                )
            )

    def test_container_run_arguments(self) -> None:
        client = _FakeClient(present_images=["python:3.11-slim"])
        sandbox = _make_sandbox(client)
        session = sandbox.create_session(
            settings=DockerSandboxSettings(
                cpu_limit=1.5,
                memory_limit="2g",
                run_args={"labels": {"team": "ml"}, "network": "host"},
            )
        )
        call = client.containers.run_calls[0]
        assert call["image"] == "python:3.11-slim"
        assert call["command"] == ["sleep", "infinity"]
        assert call["entrypoint"] == []
        assert call["detach"] is True
        assert call["name"] == f"zenml-sandbox-{session.id}"
        assert call["labels"] == {
            "team": "ml",
            "zenml-sandbox-session": session.id,
        }
        assert call["working_dir"] == "/workspace"
        assert call["nano_cpus"] == 1_500_000_000
        assert call["mem_limit"] == "2g"
        assert call["network"] == "host"

    def test_session_id_is_docker_prefixed(self) -> None:
        assert _make_session().id.startswith("docker-")


class TestExec:
    def test_exec_resolves_workdir_and_env(self) -> None:
        session = _make_session()
        session._env = {"BASE": "1"}
        session.exec(["echo", "hi"], cwd="sub", env={"X": "2"})
        call = session._container.client.api.exec_creates[0]
        assert call["workdir"] == "/workspace/sub"
        assert call["environment"] == {"BASE": "1", "X": "2"}
        assert _wrapped_command(call) == ["echo", "hi"]

    def test_exec_absolute_cwd_wins(self) -> None:
        session = _make_session()
        session.exec(["true"], cwd="/opt")
        call = session._container.client.api.exec_creates[0]
        assert call["workdir"] == "/opt"

    def test_string_command_is_split(self) -> None:
        session = _make_session()
        session.exec("echo 'hello world'")
        call = session._container.client.api.exec_creates[0]
        assert _wrapped_command(call) == ["echo", "hello world"]

    def test_collect_returns_demuxed_streams(self) -> None:
        api = _FakeAPI(
            chunks=[(b"out line 1\nout line 2\n", None), (None, b"err\n")],
            exit_code=3,
        )
        session = _make_session(api)
        output = session.exec(["prog"]).collect()
        assert output.stdout == "out line 1\nout line 2\n"
        assert output.stderr == "err\n"
        assert output.exit_code == 3

    def test_incomplete_line_is_flushed(self) -> None:
        api = _FakeAPI(chunks=[(b"no newline", None)])
        session = _make_session(api)
        output = session.exec(["prog"]).collect()
        assert output.stdout == "no newline"

    def test_wait_timeout(self) -> None:
        gate = threading.Event()
        api = _FakeAPI(gate=gate)
        session = _make_session(api)
        process = session.exec(["sleep", "60"])
        try:
            with pytest.raises(TimeoutError):
                process.wait(timeout=0.1)
        finally:
            gate.set()
        assert process.wait(timeout=5) == 0

    def test_kill_signals_recorded_pid(self) -> None:
        gate = threading.Event()
        api = _FakeAPI(gate=gate)
        session = _make_session(api)
        process = session.exec(["sleep", "60"])
        try:
            process.kill()
        finally:
            gate.set()
        exec_call = api.exec_creates[0]
        kill_call = api.exec_creates[1]
        pid_file = exec_call["cmd"][4]
        assert kill_call["cmd"] == ["sh", "-c", f'kill -9 "$(cat {pid_file})"']


class TestFileTransfer:
    def test_file_roundtrip(self, tmp_path) -> None:
        session = _make_session()
        source = tmp_path / "a.txt"
        source.write_text("hello")
        session.upload_file(str(source), "sub/a.txt")
        assert session._container.archives["/workspace/sub/a.txt"] == b"hello"
        target = tmp_path / "b.txt"
        session.download_file("sub/a.txt", str(target))
        assert target.read_text() == "hello"

    def test_download_missing_file_raises(self, tmp_path) -> None:
        session = _make_session()
        with pytest.raises(FileNotFoundError):
            session.download_file("missing.txt", str(tmp_path / "x"))


class TestLifecycle:
    def test_snapshot_commits_container(self) -> None:
        session = _make_session()
        snapshot = session.create_snapshot()
        assert snapshot.ref == "sha256:deadbeef"
        assert session._container.committed
        assert snapshot.metadata["session_id"] == session.id

    def test_restore_uses_snapshot_image(self) -> None:
        client = _FakeClient()
        sandbox = _make_sandbox(client)
        client.images.present.add("sha256:deadbeef")
        snapshot = SandboxSnapshot(
            sandbox_id=sandbox.id, ref="sha256:deadbeef"
        )
        sandbox.restore(snapshot)
        assert client.containers.run_calls[0]["image"] == "sha256:deadbeef"
        assert client.images.pulled == []

    def test_restore_rejects_foreign_snapshot(self) -> None:
        sandbox = _make_sandbox()
        snapshot = SandboxSnapshot(sandbox_id=uuid4(), ref="sha256:deadbeef")
        with pytest.raises(ValueError, match="different sandbox"):
            sandbox.restore(snapshot)

    def test_attach_finds_session_container(self) -> None:
        client = _FakeClient(present_images=["python:3.11-slim"])
        sandbox = _make_sandbox(client)
        session = sandbox.create_session()
        attached = sandbox.attach(session.id)
        assert isinstance(attached, DockerSandboxSession)
        assert attached.id == session.id
        assert attached._container is session._container

    def test_attach_unknown_session_raises(self) -> None:
        sandbox = _make_sandbox()
        with pytest.raises(KeyError):
            sandbox.attach("docker-unknown")

    def test_destroy_removes_container(self) -> None:
        session = _make_session()
        session.destroy()
        assert session._container.removed is True
        assert session.closed is True

    def test_close_keeps_container_running(self) -> None:
        session = _make_session()
        session.close()
        assert session._container.removed is False
        assert session.closed is True
