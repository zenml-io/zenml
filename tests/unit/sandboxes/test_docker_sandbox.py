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
"""Unit tests for the Docker sandbox flavor (docker SDK mocked)."""

import io
import tarfile
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from zenml.sandboxes.docker_sandbox import (
    DOCKER_SANDBOX_FLAVOR,
    DockerSandbox,
    DockerSandboxFlavor,
    DockerSandboxProcess,
    DockerSandboxSession,
    DockerSandboxSettings,
)


class _FakeAPI:
    """Low-level docker API stub covering exec_create/start/inspect."""

    def __init__(self, chunks=None, exit_code=0):
        self.chunks = chunks or []
        self.exit_code = exit_code
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
        self._running = False
        return iter(self.chunks)

    def exec_inspect(self, exec_id):
        return {
            "Running": self._running,
            "ExitCode": None if self._running else self.exit_code,
            "Pid": 42,
            "ContainerID": "c-1",
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
            raise KeyError(path)
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


def _make_session(
    api: Optional[_FakeAPI] = None,
) -> "tuple[DockerSandboxSession, _FakeContainer]":
    """Build a session around fakes without touching a daemon.

    Args:
        api: Optional fake API override.

    Returns:
        The session and its fake container.
    """
    api = api or _FakeAPI()
    container = _FakeContainer(api)
    session = object.__new__(DockerSandboxSession)
    session._container = container
    session._workdir = "/workspace"
    session._env = {"BASE": "1"}
    session.id = "docker-test"
    session._parent = MagicMock(flavor="docker", id=uuid.uuid4())
    session._closed = False
    session._destroy_on_exit = False
    session._logging_context = None
    session._logging_disabled = True
    import threading

    session._logging_lock = threading.Lock()
    return session, container


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

    def test_image_settings_capability(self) -> None:
        sandbox = object.__new__(DockerSandbox)
        settings = sandbox.image_settings("img:1")
        assert isinstance(settings, DockerSandboxSettings)
        assert settings.image == "img:1"


class TestSession:
    def test_exec_resolves_workdir_and_env(self) -> None:
        session, container = _make_session()
        process = session.exec(["echo", "hi"], cwd="sub", env={"X": "2"})
        call = container.client.api.exec_creates[0]
        assert call["workdir"] == "/workspace/sub"
        assert call["environment"] == {"BASE": "1", "X": "2"}
        assert isinstance(process, DockerSandboxProcess)

    def test_exec_absolute_cwd_wins(self) -> None:
        session, container = _make_session()
        session.exec(["true"], cwd="/opt")
        assert container.client.api.exec_creates[0]["workdir"] == "/opt"

    def test_process_collects_demuxed_streams(self) -> None:
        api = _FakeAPI(
            chunks=[(b"out line 1\nout line 2\n", None), (None, b"err\n")],
            exit_code=3,
        )
        session, _ = _make_session(api)
        output = session.exec(["prog"]).collect()
        assert output.stdout == "out line 1\nout line 2\n"
        assert output.stderr == "err\n"
        assert output.exit_code == 3

    def test_file_roundtrip(self, tmp_path) -> None:
        session, container = _make_session()
        source = tmp_path / "a.txt"
        source.write_text("hello")
        session.upload_file(str(source), "sub/a.txt")
        assert container.archives["/workspace/sub/a.txt"] == b"hello"
        target = tmp_path / "b.txt"
        session.download_file("sub/a.txt", str(target))
        assert target.read_text() == "hello"

    def test_download_missing_file_raises(self, tmp_path) -> None:
        session, _ = _make_session()
        with pytest.raises(KeyError):
            session.download_file("missing.txt", str(tmp_path / "x"))

    def test_snapshot_commits_container(self) -> None:
        session, container = _make_session()
        snapshot = session.create_snapshot()
        assert snapshot.ref == "sha256:deadbeef"
        assert container.committed
        assert snapshot.metadata["session_id"] == "docker-test"

    def test_destroy_removes_container(self) -> None:
        session, container = _make_session()
        session.destroy()
        assert container.removed is True
        assert session.closed is True

    def test_close_keeps_container_running(self) -> None:
        session, container = _make_session()
        session.close()
        assert container.removed is False
        assert session.closed is True
