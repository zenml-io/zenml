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
"""Unit tests for the Cloudflare sandbox flavor.

The bridge HTTP API is mocked via ``httpx.MockTransport`` so these tests
exercise the wiring (SSE parsing, demux, lifecycle, auth header) without
talking to a real Cloudflare Worker.
"""

import base64
import json
import os
import tempfile
import threading
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from zenml.enums import StackComponentType
from zenml.integrations.cloudflare.flavors import (
    CloudflareSandboxConfig,
    CloudflareSandboxFlavor,
    CloudflareSandboxSettings,
)
from zenml.integrations.cloudflare.flavors.cloudflare_sandbox_flavor import (
    DEFAULT_BRIDGE_TIMEOUT_MS,
)
from zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox import (
    _BRIDGE_FILE_MAX_BYTES,
    CloudflareSandbox,
    CloudflareSandboxProcess,
    CloudflareSandboxSession,
    _BridgeEvent,
    _CloudflareBridgeClient,
    _parse_sse_stream,
)
from zenml.sandboxes import BaseSandbox, SandboxExecError

WORKER_URL = "https://bridge.example.workers.dev"
API_KEY = "test-token"


def _sse_event(kind: str, data: str) -> str:
    return f"event: {kind}\ndata: {data}\n\n"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _make_client(handler: Any) -> _CloudflareBridgeClient:
    return _CloudflareBridgeClient(
        WORKER_URL, API_KEY, transport=httpx.MockTransport(handler)
    )


def _passthrough_session() -> MagicMock:
    """Stub session whose ``_wrap_stream`` returns its input iterator unchanged.

    The real ``SandboxSession._wrap_stream`` routes each line through the
    per-session log source; for unit tests we just need a passthrough so
    ``CloudflareSandboxProcess.stdout()/stderr()`` consumers can iterate.
    """
    session = MagicMock()
    session._wrap_stream.side_effect = lambda lines, **_: lines
    return session


def _make_session(
    client: _CloudflareBridgeClient,
    *,
    bridge_session_id: Optional[str] = None,
) -> CloudflareSandboxSession:
    parent = MagicMock(spec=BaseSandbox)
    parent.flavor = "cloudflare"
    parent.id = uuid4()
    return CloudflareSandboxSession(
        "sb_abc",
        client=client,
        parent=parent,
        bridge_session_id=bridge_session_id,
    )


class TestFlavorMetadata:
    def test_name_and_type(self) -> None:
        flavor = CloudflareSandboxFlavor()
        assert flavor.name == "cloudflare"
        assert flavor.type == StackComponentType.SANDBOX

    def test_logo_url(self) -> None:
        assert "sandbox/cloudflare.png" in CloudflareSandboxFlavor().logo_url

    def test_config_class(self) -> None:
        assert (
            CloudflareSandboxFlavor().config_class is CloudflareSandboxConfig
        )


class TestConfig:
    def test_worker_url_required(self) -> None:
        with pytest.raises(Exception):
            CloudflareSandboxConfig()  # type: ignore[call-arg]

    def test_is_remote(self) -> None:
        cfg = CloudflareSandboxConfig(worker_url=WORKER_URL)
        assert cfg.is_remote is True
        assert cfg.is_local is False

    def test_api_key_secret_field(self) -> None:
        from zenml.utils.secret_utils import is_secret_field

        assert is_secret_field(CloudflareSandboxConfig.model_fields["api_key"])

    def test_settings_defaults(self) -> None:
        s = CloudflareSandboxSettings()
        assert s.timeout_ms == DEFAULT_BRIDGE_TIMEOUT_MS
        assert s.cwd is None
        assert s.sandbox_environment == {}

    def test_timeout_ms_positive(self) -> None:
        with pytest.raises(Exception):
            CloudflareSandboxSettings(timeout_ms=0)

    def test_worker_url_https_accepted(self) -> None:
        cfg = CloudflareSandboxConfig(worker_url=WORKER_URL)
        assert cfg.worker_url == WORKER_URL

    def test_worker_url_http_localhost_accepted(self) -> None:
        for url in ("http://localhost:8787", "http://127.0.0.1:8787"):
            assert CloudflareSandboxConfig(worker_url=url).worker_url == url

    def test_worker_url_plain_http_rejected(self) -> None:
        with pytest.raises(ValueError, match="https"):
            CloudflareSandboxConfig(worker_url="http://example.com")


class TestSSEParser:
    def test_stdout_event(self) -> None:
        lines = iter(
            [
                "event: stdout",
                f"data: {_b64('hello')}",
                "",
            ]
        )
        events = list(_parse_sse_stream(lines))
        assert len(events) == 1
        assert events[0].kind == "stdout"
        assert events[0].data == "hello"

    def test_stderr_event(self) -> None:
        lines = iter(
            [
                "event: stderr",
                f"data: {_b64('oops')}",
                "",
            ]
        )
        events = list(_parse_sse_stream(lines))
        assert events[0].kind == "stderr"
        assert events[0].data == "oops"

    def test_exit_event(self) -> None:
        lines = iter(
            [
                "event: exit",
                'data: {"exit_code": 7}',
                "",
            ]
        )
        events = list(_parse_sse_stream(lines))
        assert events[0].kind == "exit"
        assert events[0].data == 7

    def test_error_event_raises(self) -> None:
        lines = iter(
            [
                "event: error",
                'data: {"error": "bad thing"}',
                "",
            ]
        )
        with pytest.raises(SandboxExecError, match="bad thing"):
            list(_parse_sse_stream(lines))

    def test_comments_and_unknown_events_ignored(self) -> None:
        lines = iter(
            [
                ": keep-alive",
                "event: ignored-kind",
                "data: whatever",
                "",
                "event: exit",
                'data: {"exit_code": 0}',
                "",
            ]
        )
        events = list(_parse_sse_stream(lines))
        assert len(events) == 1
        assert events[0].kind == "exit"

    def test_malformed_base64_raises(self) -> None:
        lines = iter(
            [
                "event: stdout",
                "data: !!!not-base64!!!",
                "",
            ]
        )
        with pytest.raises(SandboxExecError):
            list(_parse_sse_stream(lines))

    def test_exit_event_without_trailing_blank_line_dispatched(self) -> None:
        # Bridge may close the connection right after the last data line
        # without a trailing blank line — parser must flush the buffered
        # event on EOF, otherwise wait() reports a bogus 0 exit code.
        lines = iter(
            [
                "event: exit",
                'data: {"exit_code": 137}',
            ]
        )
        events = list(_parse_sse_stream(lines))
        assert len(events) == 1
        assert events[0].kind == "exit"
        assert events[0].data == 137

    def test_exit_event_missing_exit_code_raises(self) -> None:
        # Defending against a malformed bridge response: missing exit_code
        # must surface as an error, not be silently coerced to 0.
        lines = iter(
            [
                "event: exit",
                "data: {}",
                "",
            ]
        )
        with pytest.raises(SandboxExecError, match="missing 'exit_code'"):
            list(_parse_sse_stream(lines))


class TestBridgeClient:
    def test_auth_header_sent(self) -> None:
        captured: Dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization", "")
            return httpx.Response(200, json={"id": "sb_1"})

        client = _make_client(handler)
        try:
            client.create_sandbox()
        finally:
            client.close()
        assert captured["auth"] == f"Bearer {API_KEY}"

    def test_create_sandbox(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/sandbox"
            assert request.method == "POST"
            return httpx.Response(200, json={"id": "sb_xyz"})

        client = _make_client(handler)
        assert client.create_sandbox() == "sb_xyz"

    def test_create_sandbox_missing_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        client = _make_client(handler)
        with pytest.raises(SandboxExecError, match="missing 'id'"):
            client.create_sandbox()

    def test_delete_sandbox(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            return httpx.Response(204)

        client = _make_client(handler)
        client.delete_sandbox("sb_1")
        assert calls == ["DELETE /v1/sandbox/sb_1"]

    def test_is_running(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"running": True})

        client = _make_client(handler)
        assert client.is_running("sb_1") is True

    def test_is_running_false(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"running": False})

        client = _make_client(handler)
        assert client.is_running("sb_1") is False

    def test_is_running_gone_sandbox_is_false(self) -> None:
        # An expired/deleted sandbox 404s (or 410s) on the bridge; that's
        # an answer, not an error.
        for status in (404, 410):
            client = _make_client(
                lambda req, s=status: httpx.Response(s, text="gone")
            )
            assert client.is_running("sb_dead") is False

    def test_is_running_other_error_retries_then_raises(self) -> None:
        # is_running is a GET, so transient 5xx errors go through the
        # retry loop before surfacing.
        attempts: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return httpx.Response(503, text="unavailable")

        client = _make_client(handler)
        with patch(
            "zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox"
            ".time.sleep"
        ):
            with pytest.raises(SandboxExecError, match="503"):
                client.is_running("sb_1")
        assert len(attempts) == 4

    def test_get_retries_429_then_succeeds(self) -> None:
        attempts: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            if len(attempts) == 1:
                return httpx.Response(429, text="slow down")
            return httpx.Response(200, content=b"payload")

        client = _make_client(handler)
        with patch(
            "zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox"
            ".time.sleep"
        ):
            assert client.get_file("sb_1", "x.txt") == b"payload"
        assert len(attempts) == 2

    def test_get_persistent_503_raises_after_retries(self) -> None:
        attempts: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return httpx.Response(503, text="unavailable")

        client = _make_client(handler)
        with patch(
            "zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox"
            ".time.sleep"
        ):
            with pytest.raises(SandboxExecError, match="503"):
                client.get_file("sb_1", "x.txt")
        # Initial attempt + _MAX_RETRIES retries.
        assert len(attempts) == 4

    def test_post_exec_not_retried_on_503(self) -> None:
        # POST is not idempotent: a retried /exec could run the command
        # twice, so transient errors must surface immediately.
        attempts: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return httpx.Response(503, text="unavailable")

        client = _make_client(handler)
        with patch(
            "zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox"
            ".time.sleep"
        ) as sleep:
            with pytest.raises(SandboxExecError, match="503"):
                client.exec_stream("sb_1", ["echo", "hi"])
        assert len(attempts) == 1
        sleep.assert_not_called()

    def test_create_bridge_session_with_env(self) -> None:
        captured: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"id": "sess_1"})

        client = _make_client(handler)
        sid = client.create_bridge_session("sb_1", env={"K": "V"})
        assert sid == "sess_1"
        assert captured["body"] == {"env": {"K": "V"}}

    def test_put_file_size_limit(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        client = _make_client(handler)
        with pytest.raises(ValueError, match="exceeds the bridge limit"):
            client.put_file(
                "sb_1", "big.bin", b"x" * (_BRIDGE_FILE_MAX_BYTES + 1)
            )

    def test_put_file_session_header(self) -> None:
        captured: Dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["session"] = request.headers.get("Session-Id", "")
            captured["path"] = request.url.path
            return httpx.Response(200, json={"ok": True})

        client = _make_client(handler)
        client.put_file("sb_1", "a/b.txt", b"hello", session_id="sess_2")
        assert captured["session"] == "sess_2"
        assert captured["path"] == "/v1/sandbox/sb_1/file/a/b.txt"

    def test_put_file_rejects_path_traversal(self) -> None:
        client = _make_client(
            lambda req: httpx.Response(200, json={"ok": True})
        )
        for path in ("../x", "../../etc/passwd"):
            with pytest.raises(ValueError, match="resolves outside"):
                client.put_file("sb_1", path, b"x")

    def test_put_file_allows_dot_dot_prefixed_names(self) -> None:
        # "..foo" is a legitimate file/directory name, not a traversal.
        captured: Dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return httpx.Response(200, json={"ok": True})

        client = _make_client(handler)
        client.put_file("sb_1", "..foo/bar.txt", b"x")
        assert captured["path"] == "/v1/sandbox/sb_1/file/..foo/bar.txt"

    def test_get_file_returns_bytes(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"payload")

        client = _make_client(handler)
        assert client.get_file("sb_1", "x.txt") == b"payload"

    def test_exec_stream_surfaces_launch_errors_eagerly(self) -> None:
        # Bridge launch errors (401 etc.) must raise at exec_stream() call
        # time, not on the pump thread.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "unauthorized"})

        client = _make_client(handler)
        with pytest.raises(SandboxExecError, match="401"):
            client.exec_stream("sb_1", ["python", "-c", "print(1)"])

    def test_non_retryable_error_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="bad request")

        client = _make_client(handler)
        with pytest.raises(SandboxExecError, match="400"):
            client.create_sandbox()


class TestProcessDemux:
    def test_stdout_and_exit(self) -> None:
        session = _passthrough_session()
        events = iter(
            [
                _BridgeEvent(kind="stdout", data="line1\nline2\n"),
                _BridgeEvent(kind="exit", data=0),
            ]
        )
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        out_lines = list(proc.stdout())
        assert out_lines == ["line1\n", "line2\n"]
        assert proc.wait() == 0
        assert proc.exit_code == 0

    def test_stderr_demux(self) -> None:
        session = _passthrough_session()
        events = iter(
            [
                _BridgeEvent(kind="stderr", data="err\n"),
                _BridgeEvent(kind="stdout", data="ok\n"),
                _BridgeEvent(kind="exit", data=1),
            ]
        )
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        assert proc.wait() == 1
        assert "err\n" in list(proc.stderr())
        assert "ok\n" in list(proc.stdout())

    def test_partial_line_flushed(self) -> None:
        session = _passthrough_session()
        events = iter(
            [
                _BridgeEvent(kind="stdout", data="abc"),
                _BridgeEvent(kind="exit", data=0),
            ]
        )
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        proc.wait()
        assert list(proc.stdout()) == ["abc"]

    def test_wait_returns_captured_exit_code(self) -> None:
        session = _passthrough_session()
        events = iter([_BridgeEvent(kind="exit", data=7)])
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        assert proc.wait() == 7

    def test_wait_timeout_raises_timeout_error(self) -> None:
        release = threading.Event()

        def _block() -> Iterator[_BridgeEvent]:
            release.wait(timeout=10.0)
            yield from ()

        session = _passthrough_session()
        proc = CloudflareSandboxProcess(
            _block(), session=session, started_at=0.0
        )
        try:
            with pytest.raises(TimeoutError):
                proc.wait(timeout=0.05)
        finally:
            release.set()
            proc._pump.join(timeout=2.0)
        assert not proc._pump.is_alive()

    def test_wait_raises_when_exit_frame_missing(self) -> None:
        # Pump finishes (iterator exhausted) but never saw an exit event.
        session = _passthrough_session()
        events = iter([_BridgeEvent(kind="stdout", data="partial\n")])
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        with pytest.raises(SandboxExecError, match="without an exit frame"):
            proc.wait()

    def test_kill_unblocks_consumers(self) -> None:
        # End-to-end through session.exec: the pump blocks on a real SSE
        # body, and kill() must close the response to unblock it.
        opened = threading.Event()
        release = threading.Event()

        class _BlockingStream(httpx.SyncByteStream):
            def __iter__(self) -> Iterator[bytes]:
                opened.set()
                release.wait(timeout=10.0)
                yield b""

            def close(self) -> None:
                release.set()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                stream=_BlockingStream(),
                headers={"Content-Type": "text/event-stream"},
            )

        client = _make_client(handler)
        session = _make_session(client)
        proc = session.exec(["sleep", "60"])
        assert isinstance(proc, CloudflareSandboxProcess)
        assert opened.wait(timeout=2.0)
        proc.kill()
        # kill() must unblock wait(); no exit frame ever arrived, so this
        # surfaces as a precise killed-stream error rather than a bogus
        # exit code 0 or a vague truncation message.
        with pytest.raises(
            SandboxExecError, match=r"killed via kill\(\) or session close\(\)"
        ):
            proc.wait(timeout=2.0)
        proc._pump.join(timeout=2.0)
        assert not proc._pump.is_alive()


class TestSessionExec:
    def test_exec_sends_correct_body(self) -> None:
        captured: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/sandbox/sb_abc/exec":
                captured["body"] = json.loads(request.content.decode())
                captured["session"] = request.headers.get("Session-Id")
                sse = (
                    _sse_event("stdout", _b64("hi\n"))
                    + 'event: exit\ndata: {"exit_code": 0}\n\n'
                )
                return httpx.Response(
                    200,
                    content=sse.encode("utf-8"),
                    headers={"Content-Type": "text/event-stream"},
                )
            return httpx.Response(404)

        client = _make_client(handler)
        session = _make_session(client, bridge_session_id="s_1")
        proc = session.exec(["echo", "hi"], cwd="/workspace")
        assert proc.wait() == 0
        assert captured["body"] == {
            "argv": ["echo", "hi"],
            "timeout_ms": 120_000,
            "cwd": "/workspace",
        }
        assert captured["session"] == "s_1"

    def test_exec_string_command_shlex_split(self) -> None:
        captured: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content.decode())
            sse = 'event: exit\ndata: {"exit_code": 0}\n\n'
            return httpx.Response(
                200,
                content=sse.encode(),
                headers={"Content-Type": "text/event-stream"},
            )

        client = _make_client(handler)
        session = _make_session(client)
        proc = session.exec("python -c 'print(1)'")
        proc.wait()
        assert captured["body"]["argv"] == ["python", "-c", "print(1)"]

    def test_exec_env_inlined(self) -> None:
        captured: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content.decode())
            sse = 'event: exit\ndata: {"exit_code": 0}\n\n'
            return httpx.Response(
                200,
                content=sse.encode(),
                headers={"Content-Type": "text/event-stream"},
            )

        client = _make_client(handler)
        session = _make_session(client)
        proc = session.exec(["python"], env={"FOO": "bar"})
        proc.wait()
        argv = captured["body"]["argv"]
        assert argv[0] == "env"
        assert "FOO=bar" in argv
        assert argv[-1] == "python"


class TestSessionFileOps:
    def test_upload_and_download_roundtrip(self, tmp_path: Any) -> None:
        store: Dict[str, bytes] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            prefix = "/v1/sandbox/sb_abc/file/"
            if request.method == "PUT" and request.url.path.startswith(prefix):
                store[request.url.path[len(prefix) :]] = request.content
                return httpx.Response(200, json={"ok": True})
            if request.method == "GET" and request.url.path.startswith(prefix):
                key = request.url.path[len(prefix) :]
                return httpx.Response(200, content=store[key])
            return httpx.Response(404)

        client = _make_client(handler)
        session = _make_session(client)
        src = tmp_path / "src.txt"
        src.write_bytes(b"hello world")
        session.upload_file(str(src), "data/src.txt")
        assert store["data/src.txt"] == b"hello world"

        dst = tmp_path / "dst.txt"
        session.download_file("data/src.txt", str(dst))
        assert dst.read_bytes() == b"hello world"


class TestSessionLifecycle:
    def test_close_deletes_bridge_session(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            return httpx.Response(204)

        client = _make_client(handler)
        session = _make_session(client, bridge_session_id="sess_1")
        session.close()
        assert "DELETE /v1/sandbox/sb_abc/session/sess_1" in calls
        # Idempotent.
        calls.clear()
        session.close()
        assert calls == []

    def test_direct_close_ends_logging_context(self) -> None:
        # Users may call close() without the context manager, so close()
        # itself must end the logging context, not just __exit__.
        client = _make_client(lambda r: httpx.Response(204))
        session = _make_session(client, bridge_session_id="sess_1")
        log_ctx = MagicMock()
        session._logging_context = log_ctx
        session.close()
        log_ctx.end.assert_called_once()
        assert session._logging_context is None

    def test_close_then_exit_does_not_raise(self) -> None:
        client = _make_client(lambda r: httpx.Response(204))
        session = _make_session(client, bridge_session_id="sess_1")
        session._logging_context = MagicMock()
        with session:
            session.close()

    def test_destroy_deletes_sandbox(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            return httpx.Response(204)

        client = _make_client(handler)
        session = _make_session(client)
        session.destroy()
        assert "DELETE /v1/sandbox/sb_abc" in calls
        assert session.closed is True

    def test_upload_rejects_oversized_file_before_reading(self) -> None:
        # The size check must run on the path, not after loading the
        # whole file into memory.
        client = _make_client(lambda r: httpx.Response(204))
        session = _make_session(client)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.truncate(_BRIDGE_FILE_MAX_BYTES + 1)  # sparse, no real I/O
            path = f.name
        try:
            with pytest.raises(ValueError, match="upload limit"):
                session.upload_file(path, "big.bin")
        finally:
            os.unlink(path)

    def test_destroy_raises_and_keeps_handle_open_on_failure(self) -> None:
        # A failed delete must surface (the sandbox keeps running until
        # TTL) and leave the handle open so destroy() can be retried.
        statuses = iter([500, 204])

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "DELETE":
                return httpx.Response(next(statuses))
            return httpx.Response(204)

        client = _make_client(handler)
        session = _make_session(client)
        with pytest.raises(RuntimeError, match="Failed to delete"):
            session.destroy()
        assert session.closed is False
        session.destroy()  # retry succeeds
        assert session.closed is True

    def test_destroy_succeeds_when_sandbox_already_gone(self) -> None:
        # A 404/410 on DELETE means the sandbox already expired (TTL) or
        # was destroyed before — the desired end state, so destroy() must
        # succeed and close the handle instead of raising forever.
        for status in (404, 410):

            def handler(
                request: httpx.Request, s: int = status
            ) -> httpx.Response:
                if request.method == "DELETE":
                    return httpx.Response(s, text="gone")
                return httpx.Response(204)

            client = _make_client(handler)
            session = _make_session(client)
            session.destroy()
            assert session.closed is True

    def test_close_kills_unfinished_exec_streams(self) -> None:
        # close() must not leave the local SSE response + pump thread
        # alive for a still-running command; the remote command keeps
        # going, but local resources die with the handle.
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/exec"):
                # stdout frame but no exit frame: command still running.
                return httpx.Response(
                    200,
                    headers={"Content-Type": "text/event-stream"},
                    text=_sse_event("stdout", _b64("partial\n")),
                )
            return httpx.Response(204)

        client = _make_client(handler)
        session = _make_session(client)
        process = session.exec(["sleep", "3600"])
        session.close()
        assert process._killed.is_set()

    def test_dashboard_url_none(self) -> None:
        client = _make_client(lambda r: httpx.Response(200, json={"id": "x"}))
        session = _make_session(client)
        assert session._get_dashboard_url() is None


class TestComponent:
    def _make_component(self, **config_kwargs: Any) -> CloudflareSandbox:
        from datetime import datetime

        return CloudflareSandbox(
            name="cf-sandbox",
            id=uuid4(),
            config=CloudflareSandboxConfig(
                worker_url=WORKER_URL, api_key=API_KEY, **config_kwargs
            ),
            flavor="cloudflare",
            type=StackComponentType.SANDBOX,
            user=uuid4(),
            project=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    def test_create_session_with_env(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            if request.url.path == "/v1/sandbox":
                return httpx.Response(200, json={"id": "sb_new"})
            if request.url.path == "/v1/sandbox/sb_new/session":
                return httpx.Response(200, json={"id": "sess_new"})
            return httpx.Response(404)

        component = self._make_component()
        component._client = _make_client(handler)
        settings = CloudflareSandboxSettings(sandbox_environment={"K": "V"})
        sess = component.create_session(settings)
        assert isinstance(sess, CloudflareSandboxSession)
        assert sess.id == "sb_new"
        assert "POST /v1/sandbox" in calls
        assert "POST /v1/sandbox/sb_new/session" in calls

    def test_create_session_cleans_up_sandbox_on_session_failure(
        self,
    ) -> None:
        # If bridge-session creation fails after the sandbox was created,
        # the sandbox must be deleted instead of leaking until its TTL.
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            if request.method == "POST" and request.url.path == "/v1/sandbox":
                return httpx.Response(200, json={"id": "sb_leak"})
            if request.url.path == "/v1/sandbox/sb_leak/session":
                return httpx.Response(500, text="session backend down")
            if (
                request.method == "DELETE"
                and request.url.path == "/v1/sandbox/sb_leak"
            ):
                return httpx.Response(204)
            return httpx.Response(404)

        component = self._make_component()
        component._client = _make_client(handler)
        settings = CloudflareSandboxSettings(sandbox_environment={"K": "V"})
        with pytest.raises(SandboxExecError, match="500"):
            component.create_session(settings)
        assert "DELETE /v1/sandbox/sb_leak" in calls

    def test_create_session_without_env_skips_bridge_session(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            if request.url.path == "/v1/sandbox":
                return httpx.Response(200, json={"id": "sb_n"})
            return httpx.Response(404)

        component = self._make_component()
        component._client = _make_client(handler)
        sess = component.create_session()
        assert isinstance(sess, CloudflareSandboxSession)
        assert all("/session" not in c for c in calls)

    def test_attach_running(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"running": True})

        component = self._make_component()
        component._client = _make_client(handler)
        sess = component.attach("sb_existing")
        assert sess.id == "sb_existing"

    def test_attach_with_env_creates_bridge_session(self) -> None:
        # attach() must restore sandbox_environment the same way
        # create_session does: via an owned bridge session, not silently
        # dropping it.
        captured: Dict[str, Any] = {}
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            if request.url.path == "/v1/sandbox/sb_existing/running":
                return httpx.Response(200, json={"running": True})
            if request.url.path == "/v1/sandbox/sb_existing/session":
                if request.method == "POST":
                    captured["body"] = json.loads(request.content.decode())
                    return httpx.Response(200, json={"id": "sess_att"})
            if request.url.path.startswith("/v1/sandbox/sb_existing/session/"):
                return httpx.Response(204)
            return httpx.Response(404)

        component = self._make_component(sandbox_environment={"K": "V"})
        component._client = _make_client(handler)
        sess = component.attach("sb_existing")
        assert isinstance(sess, CloudflareSandboxSession)
        assert captured["body"] == {"env": {"K": "V"}}
        assert sess._bridge_session_id == "sess_att"
        # The attached session owns the bridge session and deletes it on
        # close.
        sess.close()
        assert "DELETE /v1/sandbox/sb_existing/session/sess_att" in calls

    def test_attach_not_running_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"running": False})

        component = self._make_component()
        component._client = _make_client(handler)
        with pytest.raises(RuntimeError, match="not running"):
            component.attach("sb_dead")
