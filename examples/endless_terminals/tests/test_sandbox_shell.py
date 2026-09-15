"""FIFO shell deadlines and optional cached-image Docker integration."""

import base64
import os
import subprocess
import time
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from runtime.sandbox_shell import MAX_OUTPUT, SandboxShell


def test_expired_episode_stops_without_remote_command() -> None:
    """An expired controller deadline prevents another remote operation."""
    session = Mock()
    shell = SandboxShell(session, command_timeout=1, episode_timeout=1)
    shell._process = Mock()
    shell._deadline = time.monotonic() - 1
    assert not shell.execute("echo late")[0]
    assert shell.stopped
    session.exec.assert_not_called()


def test_upload_timeout_stops_terminal() -> None:
    """A stalled public transfer cannot block the controller indefinitely."""
    session = Mock()
    session.upload_file.side_effect = lambda *_: time.sleep(0.2)
    shell = SandboxShell(session, command_timeout=0.03, episode_timeout=1)
    shell._process = Mock()
    shell._deadline = time.monotonic() + 1
    start = time.monotonic()
    success, message = shell.execute("echo hello")
    assert not success and "deadline" in message
    assert time.monotonic() - start < 0.15
    assert shell.stopped
    session.exec.assert_not_called()


def test_oversized_command_stops_without_transfer() -> None:
    """Large commands fail before consuming remote resources."""
    session = Mock()
    shell = SandboxShell(session, command_timeout=1, episode_timeout=1)
    shell._process = Mock()
    shell._deadline = time.monotonic() + 1
    assert not shell.execute("x" * (MAX_OUTPUT + 1))[0]
    assert shell.stopped
    session.upload_file.assert_not_called()


def test_stream_overflow_is_bounded() -> None:
    """The adapter rejects a stream chunk beyond its queue byte budget."""
    shell = SandboxShell(Mock(), command_timeout=1, episode_timeout=1)
    shell._process = Mock()
    frame = base64.b64encode(b"x" * 4096).decode() + "\n"
    shell._process.stdout.return_value = iter([frame] * 66)
    shell._drain()
    assert shell._failure.is_set()
    assert shell._queued_bytes <= MAX_OUTPUT + 256


@pytest.mark.skipif(
    not os.environ.get("ENDLESS_DOCKER_TEST_IMAGE"),
    reason="Set ENDLESS_DOCKER_TEST_IMAGE to an existing local image",
)
def test_public_docker_session_preserves_state_and_stops_on_timeout() -> None:
    """Exercise FIFO state and timeout behavior without image pulls."""
    from zenml.enums import StackComponentType
    from zenml.sandboxes.docker_sandbox import (
        DockerSandbox,
        DockerSandboxConfig,
    )

    sandbox = DockerSandbox(
        name="fifo-test",
        id=uuid4(),
        flavor="docker",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        config=DockerSandboxConfig(
            image=os.environ["ENDLESS_DOCKER_TEST_IMAGE"],
            pull_policy="never",
            workdir="/home/user",
            cpu_limit=0.5,
            memory_limit="256m",
            run_args={"network_mode": "none"},
        ),
    )
    session_id = None
    try:
        with sandbox.create_session(destroy_on_exit=True) as session:
            session_id = session.id
            shell = SandboxShell(
                session, command_timeout=5, episode_timeout=30
            )
            try:
                shell.start()
                assert shell.execute(
                    "mkdir /tmp/state; cd /tmp/state; export CHECK_VALUE=kept"
                )[0]
                ok, text = shell.execute(
                    'printf "%s:%s" "$PWD" "$CHECK_VALUE"'
                )
                assert ok and text == "/tmp/state:kept"
                assert not shell.execute("false")[0]
                assert not shell.stopped
                # No newline is emitted until after the byte limit is exceeded.
                success, text = shell.execute(
                    "python3 -c 'import sys; sys.stdout.write(\"x\" * 524288)'"
                )
                assert not success and shell.stopped
                assert len(text.encode()) < MAX_OUTPUT + 512
                shell.close()
                shell = SandboxShell(
                    session, command_timeout=5, episode_timeout=30
                )
                shell.start()
                shell.command_timeout = 0.5
                assert not shell.execute("sleep 10")[0]
                assert shell.stopped
                assert shell.execute("echo late") == (
                    False,
                    "Terminal is stopped",
                )
            finally:
                shell.close()
    finally:
        if session_id:
            remaining = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    "label=zenml-sandbox-session=" + session_id,
                    "--format",
                    "{{.ID}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            assert not remaining.stdout.strip()


def test_malformed_frame_stops_stream() -> None:
    """Malformed transport framing never becomes agent output."""
    shell = SandboxShell(Mock(), command_timeout=1, episode_timeout=1)
    shell._process = Mock()
    shell._process.stdout.return_value = iter(["invalid % framing\n"])
    shell._drain()
    assert shell._failure.is_set()
    assert shell._output.empty()


def test_control_commands_never_kill_the_shared_session() -> None:
    """Successful setup, dispatch and close cannot trigger backend-wide kill."""
    import queue
    import re
    import threading
    from pathlib import Path
    from typing import Iterator

    frames: queue.Queue[str] = queue.Queue()
    ended = threading.Event()
    control = Mock()
    control.wait.return_value = 0
    control.kill.side_effect = AssertionError("Kill would destroy the session")
    persistent = Mock()
    persistent.kill.side_effect = AssertionError(
        "Per-process kill unsupported"
    )

    def output() -> Iterator[str]:
        """Deliver fake backend frames until the owner terminates the session.

        Yields:
            Base64 output frames.
        """
        while not ended.is_set():
            try:
                yield frames.get(timeout=0.05)
            except queue.Empty:
                pass

    def upload(local: str, remote: str) -> None:
        """Return a successful command marker from the fake persistent shell.

        Args:
            local: Controller script path.
            remote: Remote script path.
        """
        match = re.search(r"ENDLESS_[a-f0-9]+", Path(local).read_text())
        assert match is not None
        frames.put(
            base64.b64encode(
                b"\x1e" + match[0].encode() + b":0\x1f\n"
            ).decode()
            + "\n"
        )

    persistent.stdout.side_effect = output
    session = Mock()
    session.exec.side_effect = lambda command: (
        persistent if "exec 3<>" in command[-1] else control
    )
    session.upload_file.side_effect = upload
    shell = SandboxShell(session, command_timeout=1, episode_timeout=5)
    try:
        shell.start()
        assert shell.execute("printf ready")[0]
        shell.close()
        assert shell.stopped
        control.kill.assert_not_called()
        persistent.kill.assert_not_called()
    finally:
        ended.set()
