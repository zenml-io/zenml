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
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from zenml.enums import StackComponentType
from zenml.integrations.cloudflare.flavors import (
    CloudflareSandboxConfig,
    CloudflareSandboxFlavor,
    CloudflareSandboxSettings,
)
from zenml.integrations.cloudflare.sandboxes.cloudflare_sandbox import (
    _BRIDGE_FILE_MAX_BYTES,
    CloudflareSandbox,
    CloudflareSandboxProcess,
    CloudflareSandboxSession,
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
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(
        base_url=WORKER_URL, transport=transport, timeout=5.0
    )
    return _CloudflareBridgeClient(
        WORKER_URL, API_KEY, http_client=http_client
    )


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
        assert s.base_image is None
        assert s.timeout_ms is None
        assert s.cwd is None
        assert s.sandbox_environment == {}

    def test_timeout_ms_positive(self) -> None:
        with pytest.raises(Exception):
            CloudflareSandboxSettings(timeout_ms=0)


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

    def test_create_bridge_session_with_env(self) -> None:
        captured: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"id": "sess_1"})

        client = _make_client(handler)
        sid = client.create_bridge_session("sb_1", env={"K": "V"})
        assert sid == "sess_1"
        assert captured["body"] == {"env": {"K": "V"}}

    def test_create_bridge_session_falls_back_on_422(self) -> None:
        calls: List[Dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = (
                json.loads(request.content.decode())
                if request.content
                else None
            )
            calls.append({"body": body})
            if body is not None:
                return httpx.Response(422, json={"error": "no env"})
            return httpx.Response(200, json={"id": "sess_x"})

        client = _make_client(handler)
        sid = client.create_bridge_session("sb_1", env={"K": "V"})
        assert sid == "sess_x"
        assert len(calls) == 2
        assert calls[0]["body"] == {"env": {"K": "V"}}
        assert calls[1]["body"] is None

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

    def test_get_file_returns_bytes(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"payload")

        client = _make_client(handler)
        assert client.get_file("sb_1", "x.txt") == b"payload"

    def test_non_retryable_error_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="bad request")

        client = _make_client(handler)
        with pytest.raises(SandboxExecError, match="400"):
            client.create_sandbox()


class TestProcessDemux:
    def test_stdout_and_exit(self) -> None:
        session = MagicMock()
        events = iter(
            [
                type("E", (), {"kind": "stdout", "data": "line1\nline2\n"})(),
                type("E", (), {"kind": "exit", "data": 0})(),
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
        session = MagicMock()
        events = iter(
            [
                type("E", (), {"kind": "stderr", "data": "err\n"})(),
                type("E", (), {"kind": "stdout", "data": "ok\n"})(),
                type("E", (), {"kind": "exit", "data": 1})(),
            ]
        )
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        assert proc.wait() == 1
        assert "err\n" in list(proc.stderr())
        assert "ok\n" in list(proc.stdout())

    def test_partial_line_flushed(self) -> None:
        session = MagicMock()
        events = iter(
            [
                type("E", (), {"kind": "stdout", "data": "abc"})(),
                type("E", (), {"kind": "exit", "data": 0})(),
            ]
        )
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        proc.wait()
        assert list(proc.stdout()) == ["abc"]

    def test_wait_with_timeout_raises(self) -> None:
        session = MagicMock()
        events = iter([type("E", (), {"kind": "exit", "data": 0})()])
        proc = CloudflareSandboxProcess(
            events, session=session, started_at=0.0
        )
        proc.wait()
        with pytest.raises(NotImplementedError):
            proc.wait(timeout=1.0)


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

    def test_destroy_deletes_sandbox(self) -> None:
        calls: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            return httpx.Response(204)

        client = _make_client(handler)
        session = _make_session(client)
        session.destroy()
        assert "DELETE /v1/sandbox/sb_abc" in calls

    def test_dashboard_url_none(self) -> None:
        client = _make_client(lambda r: httpx.Response(200, json={"id": "x"}))
        session = _make_session(client)
        assert session._get_dashboard_url() is None


class TestComponent:
    def _make_component(self) -> CloudflareSandbox:
        from datetime import datetime

        return CloudflareSandbox(
            name="cf-sandbox",
            id=uuid4(),
            config=CloudflareSandboxConfig(
                worker_url=WORKER_URL, api_key=API_KEY
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

    def test_attach_not_running_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"running": False})

        component = self._make_component()
        component._client = _make_client(handler)
        with pytest.raises(RuntimeError, match="not running"):
            component.attach("sb_dead")
