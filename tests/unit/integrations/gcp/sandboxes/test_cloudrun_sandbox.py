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
"""Unit tests for the Cloud Run sandbox flavor.

The bridge HTTP API is mocked via ``httpx.MockTransport`` so these tests
exercise the wiring (SSE parsing, demux, lifecycle, ID-token auth headers)
without a real bridge service or Google credentials.
"""

import base64
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from zenml.enums import StackComponentType
from zenml.integrations.gcp.flavors import (
    CloudRunSandboxConfig,
    CloudRunSandboxFlavor,
    CloudRunSandboxSettings,
)
from zenml.integrations.gcp.sandboxes.cloudrun_sandbox import (
    _BRIDGE_FILE_MAX_BYTES,
    CloudRunSandbox,
    CloudRunSandboxProcess,
    CloudRunSandboxSession,
    _BridgeEvent,
    _CloudRunBridgeClient,
    _parse_sse_stream,
)
from zenml.sandboxes import (
    BaseSandbox,
    SandboxExecError,
    SandboxSnapshot,
)

SERVICE_URL = "https://zenml-sandbox-bridge-abc123-ew.a.run.app"


class _StaticCredentials:
    """Test double for Google ID-token credentials."""

    def __init__(self, token: str = "test-id-token") -> None:
        self.token = token
        self.refresh_count = 0

    @property
    def valid(self) -> bool:
        return self.refresh_count > 0

    def refresh(self, request: Any) -> None:
        self.refresh_count += 1


def _sse_event(kind: str, data: str) -> str:
    return f"event: {kind}\ndata: {data}\n\n"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _make_client(
    handler: Any, credentials: Optional[_StaticCredentials] = None
) -> _CloudRunBridgeClient:
    return _CloudRunBridgeClient(
        SERVICE_URL,
        credentials,
        transport=httpx.MockTransport(handler),
    )


def _make_session(
    client: _CloudRunBridgeClient,
    *,
    session_env: Optional[Dict[str, str]] = None,
    snapshot_uri_prefix: Optional[str] = None,
    default_cwd: Optional[str] = None,
) -> CloudRunSandboxSession:
    parent = MagicMock(spec=BaseSandbox)
    parent.flavor = "cloudrun"
    parent.id = uuid4()
    return CloudRunSandboxSession(
        "sb-0123456789ab",
        client=client,
        parent=parent,
        session_env=session_env,
        snapshot_uri_prefix=snapshot_uri_prefix,
        default_cwd=default_cwd,
    )


def _passthrough_wrap_stream(session: CloudRunSandboxSession) -> None:
    """Bypass step-log routing so tests can iterate raw process output."""
    session._wrap_stream = lambda lines, **_: lines  # type: ignore[method-assign]


class TestFlavorMetadata:
    def test_name_and_type(self) -> None:
        flavor = CloudRunSandboxFlavor()
        assert flavor.name == "cloudrun"
        assert flavor.type == StackComponentType.SANDBOX
        assert flavor.config_class is CloudRunSandboxConfig

    def test_service_connector_requirements(self) -> None:
        requirements = CloudRunSandboxFlavor().service_connector_requirements
        assert requirements is not None
        assert requirements.connector_type == "gcp"
        assert requirements.resource_type == "gcp-generic"


class TestConfigValidation:
    def test_https_url_accepted(self) -> None:
        config = CloudRunSandboxConfig(service_url=SERVICE_URL)
        assert config.service_url == SERVICE_URL
        assert config.is_remote is True
        assert config.is_local is False

    def test_http_localhost_accepted(self) -> None:
        config = CloudRunSandboxConfig(service_url="http://localhost:8080")
        assert config.service_url == "http://localhost:8080"

    def test_plain_http_rejected(self) -> None:
        with pytest.raises(ValueError, match="https"):
            CloudRunSandboxConfig(service_url="http://bridge.example.com")

    def test_snapshot_prefix_requires_gs_scheme(self) -> None:
        with pytest.raises(ValueError, match="gs://"):
            CloudRunSandboxConfig(
                service_url=SERVICE_URL,
                snapshot_uri_prefix="s3://bucket/prefix",
            )

    def test_snapshot_prefix_trailing_slash_stripped(self) -> None:
        config = CloudRunSandboxConfig(
            service_url=SERVICE_URL,
            snapshot_uri_prefix="gs://bucket/prefix/",
        )
        assert config.snapshot_uri_prefix == "gs://bucket/prefix"

    def test_settings_defaults(self) -> None:
        settings = CloudRunSandboxSettings()
        assert settings.timeout_ms == 120_000
        assert settings.cwd is None
        assert settings.allow_egress is False
        assert settings.sandbox_environment == {}


class TestSseParsing:
    def test_interleaved_stdout_stderr_and_exit(self) -> None:
        stream = (
            _sse_event("stdout", _b64("out line\n"))
            + _sse_event("stderr", _b64("err line\n"))
            + _sse_event("exit", json.dumps({"exit_code": 3}))
        )
        events = list(_parse_sse_stream(iter(stream.split("\n"))))
        assert events == [
            _BridgeEvent(kind="stdout", data="out line\n"),
            _BridgeEvent(kind="stderr", data="err line\n"),
            _BridgeEvent(kind="exit", data=3),
        ]

    def test_error_frame_raises(self) -> None:
        stream = _sse_event("error", json.dumps({"error": "boom"}))
        with pytest.raises(SandboxExecError, match="boom"):
            list(_parse_sse_stream(iter(stream.split("\n"))))

    def test_exit_frame_missing_code_raises(self) -> None:
        stream = _sse_event("exit", "{}")
        with pytest.raises(SandboxExecError, match="exit_code"):
            list(_parse_sse_stream(iter(stream.split("\n"))))

    def test_trailing_event_without_blank_line_flushed(self) -> None:
        raw = 'event: exit\ndata: {"exit_code": 0}'
        events = list(_parse_sse_stream(iter(raw.split("\n"))))
        assert events == [_BridgeEvent(kind="exit", data=0)]

    def test_comments_and_unknown_events_ignored(self) -> None:
        stream = (
            ": keep-alive\n\n"
            + _sse_event("heartbeat", "x")
            + _sse_event("exit", json.dumps({"exit_code": 0}))
        )
        events = list(_parse_sse_stream(iter(stream.split("\n"))))
        assert events == [_BridgeEvent(kind="exit", data=0)]


class TestBridgeClient:
    def test_create_sandbox_payload_and_auth_header(self) -> None:
        seen: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["auth"] = request.headers.get("Authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "sb-0123456789ab"})

        credentials = _StaticCredentials()
        client = _make_client(handler, credentials)
        client.create_sandbox("sb-0123456789ab", allow_egress=True)

        assert seen["path"] == "/v1/sandbox"
        assert seen["auth"] == "Bearer test-id-token"
        assert seen["body"] == {
            "id": "sb-0123456789ab",
            "allow_egress": True,
        }
        assert credentials.refresh_count == 1

    def test_create_sandbox_with_import_tar(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["id"] == "sb-0123456789ab"
            assert body["import_tar_uri"] == "gs://bucket/snap.tar"
            return httpx.Response(200, json={"id": "sb-0123456789ab"})

        client = _make_client(handler)
        client.create_sandbox(
            "sb-0123456789ab", import_tar_uri="gs://bucket/snap.tar"
        )

    def test_no_auth_header_when_unauthenticated(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "Authorization" not in request.headers
            return httpx.Response(200, json={"id": "sb-0123456789ab"})

        client = _make_client(handler, credentials=None)
        client.create_sandbox("sb-0123456789ab")

    def test_kill_exec_tolerates_404(self) -> None:
        client = _make_client(lambda _: httpx.Response(404))
        client.kill_exec("sb-0123456789ab", "exec-123")

    def test_delete_tolerates_404(self) -> None:
        client = _make_client(lambda _: httpx.Response(404))
        client.delete_sandbox("sb-0123456789ab")

    def test_is_running(self) -> None:
        client = _make_client(
            lambda _: httpx.Response(200, json={"running": True})
        )
        assert client.is_running("sb-0123456789ab") is True

        client = _make_client(lambda _: httpx.Response(404))
        assert client.is_running("sb-0123456789ab") is False

    def test_snapshot_sandbox(self) -> None:
        seen: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={})

        client = _make_client(handler)
        client.snapshot_sandbox("sb-0123456789ab", "gs://bucket/snap.tar")
        assert seen["path"] == "/v1/sandbox/sb-0123456789ab/snapshot"
        assert seen["body"] == {"gcs_uri": "gs://bucket/snap.tar"}

    def test_get_retries_transient_errors(self) -> None:
        calls: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) < 3:
                return httpx.Response(503)
            return httpx.Response(200, json={"running": True})

        client = _make_client(handler)
        assert client.is_running("sb-0123456789ab") is True
        assert len(calls) == 3

    def test_post_never_retried(self) -> None:
        calls: List[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(503)

        client = _make_client(handler)
        with pytest.raises(SandboxExecError, match="503"):
            client.create_sandbox("sb-0123456789ab")
        assert len(calls) == 1

    def test_upload_rejects_oversized_file(self) -> None:
        session = _make_session(_make_client(lambda _: httpx.Response(200)))
        with tempfile.TemporaryDirectory() as tmp:
            big = os.path.join(tmp, "big.bin")
            # Sparse file: sets the size without writing 32 MiB of data.
            with open(big, "wb") as f:
                f.truncate(_BRIDGE_FILE_MAX_BYTES + 1)
            with pytest.raises(ValueError, match="upload limit"):
                session.upload_file(big, "/data/big.bin")

    def test_file_paths_reject_traversal(self) -> None:
        client = _make_client(lambda _: httpx.Response(200))
        with pytest.raises(ValueError, match="outside"):
            client.get_file("sb-0123456789ab", "../etc/passwd")

    def test_exec_stream_env_and_body(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["argv"] == ["echo", "hi"]
            assert body["env"] == {"FOO": "bar"}
            assert body["cwd"] == "/workspace"
            assert body["timeout_ms"] == 5000
            return httpx.Response(
                200,
                content=_sse_event("exit", json.dumps({"exit_code": 0})),
                headers={"Content-Type": "text/event-stream"},
            )

        client = _make_client(handler)
        _, events = client.exec_stream(
            "sb-0123456789ab",
            ["echo", "hi"],
            cwd="/workspace",
            env={"FOO": "bar"},
            timeout_ms=5000,
        )
        assert list(events) == [_BridgeEvent(kind="exit", data=0)]


class TestProcess:
    def _make_process(
        self,
        events: List[_BridgeEvent],
        *,
        client: Any = None,
        exec_id: Optional[str] = None,
    ) -> CloudRunSandboxProcess:
        session = MagicMock()
        session._wrap_stream.side_effect = lambda lines, **_: lines
        return CloudRunSandboxProcess(
            iter(events),
            session=session,
            started_at=0.0,
            client=client,
            sandbox_id="sb-0123456789ab",
            exec_id=exec_id,
        )

    def test_demux_and_wait(self) -> None:
        process = self._make_process(
            [
                _BridgeEvent(kind="stdout", data="a\nb\n"),
                _BridgeEvent(kind="stderr", data="warn\n"),
                _BridgeEvent(kind="exit", data=7),
            ]
        )
        assert list(process.stdout()) == ["a\n", "b\n"]
        assert list(process.stderr()) == ["warn\n"]
        assert process.wait(timeout=5) == 7
        assert process.exit_code == 7

    def test_partial_line_flushed_on_stream_end(self) -> None:
        process = self._make_process(
            [
                _BridgeEvent(kind="stdout", data="no newline"),
                _BridgeEvent(kind="exit", data=0),
            ]
        )
        assert list(process.stdout()) == ["no newline"]

    def test_wait_surfaces_missing_exit_frame(self) -> None:
        process = self._make_process([_BridgeEvent(kind="stdout", data="x\n")])
        with pytest.raises(SandboxExecError, match="without an exit frame"):
            process.wait(timeout=5)

    def test_kill_unblocks_wait(self) -> None:
        process = self._make_process([_BridgeEvent(kind="stdout", data="x\n")])
        process.kill()
        with pytest.raises(SandboxExecError, match="killed"):
            process.wait(timeout=5)

    def test_kill_terminates_remote_command(self) -> None:
        client = MagicMock()
        process = self._make_process(
            [_BridgeEvent(kind="stdout", data="x\n")],
            client=client,
            exec_id="exec-123",
        )
        process.kill()
        client.kill_exec.assert_called_once_with("sb-0123456789ab", "exec-123")

    def test_buffer_byte_cap_drops_oldest(self) -> None:
        # Two ~1 MiB newline-free chunks each flush as a synthetic line;
        # with a smaller cap the oldest is dropped rather than retained.
        import zenml.integrations.gcp.sandboxes.cloudrun_sandbox as mod

        chunk = "a" * (mod._STREAM_REMAINDER_MAX_BYTES + 1)
        with patch.object(mod, "_STREAM_BUFFER_MAX_BYTES", len(chunk) + 10):
            process = self._make_process(
                [
                    _BridgeEvent(kind="stdout", data=chunk),
                    _BridgeEvent(kind="stdout", data=chunk),
                    _BridgeEvent(kind="exit", data=0),
                ]
            )
            process.wait(timeout=5)
            # Only the most recent chunk survives the byte cap.
            assert len(list(process.stdout())) == 1


class TestSession:
    def test_exec_merges_session_env(self) -> None:
        seen: Dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                content=_sse_event("exit", json.dumps({"exit_code": 0})),
                headers={"Content-Type": "text/event-stream"},
            )

        session = _make_session(
            _make_client(handler),
            session_env={"BASE": "1", "OVERRIDE": "session"},
        )
        _passthrough_wrap_stream(session)
        process = session.exec(
            "echo hi", env={"OVERRIDE": "exec", "EXTRA": "2"}
        )
        assert process.wait(timeout=5) == 0
        assert seen["body"]["env"] == {
            "BASE": "1",
            "OVERRIDE": "exec",
            "EXTRA": "2",
        }
        assert seen["body"]["argv"] == ["echo", "hi"]

    def test_upload_and_download_roundtrip(self) -> None:
        stored: Dict[str, bytes] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                stored[request.url.path] = request.content
                return httpx.Response(200, json={"written": "x"})
            return httpx.Response(200, content=stored[request.url.path])

        session = _make_session(_make_client(handler))
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.txt")
            with open(src, "w") as f:
                f.write("payload")
            session.upload_file(src, "/data/in.txt")

            dst = os.path.join(tmp, "out.txt")
            session.download_file("/data/in.txt", dst)
            with open(dst) as f:
                assert f.read() == "payload"

    def test_relative_paths_resolve_against_default_cwd(self) -> None:
        # A relative remote_path must land under the session's default cwd
        # (the same directory exec() uses), not at the sandbox root, so
        # exec and file transfer agree on where a relative path lives.
        stored: Dict[str, bytes] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                stored[request.url.path] = request.content
                return httpx.Response(200, json={"written": "x"})
            return httpx.Response(200, content=stored[request.url.path])

        session = _make_session(
            _make_client(handler), default_cwd="/tmp/workspace"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.txt")
            with open(src, "w") as f:
                f.write("payload")
            session.upload_file(src, "foo.txt")

            assert (
                "/v1/sandbox/sb-0123456789ab/file/tmp/workspace/foo.txt"
                in (stored)
            )

            dst = os.path.join(tmp, "out.txt")
            session.download_file("foo.txt", dst)
            with open(dst) as f:
                assert f.read() == "payload"

    def test_absolute_paths_ignore_default_cwd(self) -> None:
        stored: Dict[str, bytes] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                stored[request.url.path] = request.content
                return httpx.Response(200, json={"written": "x"})
            return httpx.Response(200, content=stored[request.url.path])

        session = _make_session(
            _make_client(handler), default_cwd="/tmp/workspace"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.txt")
            with open(src, "w") as f:
                f.write("payload")
            session.upload_file(src, "/data/in.txt")

            # Leading slash is stripped for URL composition, but the path is
            # anchored at the sandbox root — not joined onto default_cwd.
            assert "/v1/sandbox/sb-0123456789ab/file/data/in.txt" in stored

    def test_relative_escape_above_default_cwd_refused(self) -> None:
        session = _make_session(
            _make_client(lambda _: httpx.Response(200)),
            default_cwd="/tmp/workspace",
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.txt")
            with open(src, "w") as f:
                f.write("payload")
            with pytest.raises(ValueError, match="outside"):
                session.upload_file(src, "../../etc/passwd")

    def test_snapshot_requires_prefix(self) -> None:
        session = _make_session(_make_client(lambda _: httpx.Response(200)))
        with pytest.raises(NotImplementedError, match="snapshot_uri_prefix"):
            session.create_snapshot()

    def test_snapshot_returns_gcs_ref(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["gcs_uri"].startswith(
                "gs://bucket/prefix/sb-0123456789ab-"
            )
            return httpx.Response(200, json={})

        session = _make_session(
            _make_client(handler),
            snapshot_uri_prefix="gs://bucket/prefix",
        )
        snapshot = session.create_snapshot()
        assert isinstance(snapshot, SandboxSnapshot)
        assert snapshot.ref.startswith("gs://bucket/prefix/")
        assert snapshot.sandbox_id == session._parent.id

    def test_destroy_deletes_sandbox(self) -> None:
        deleted: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "DELETE":
                deleted.append(request.url.path)
            return httpx.Response(200, json={})

        session = _make_session(_make_client(handler))
        session.destroy()
        assert deleted == ["/v1/sandbox/sb-0123456789ab"]
        assert session.closed

    def test_closed_session_rejects_exec(self) -> None:
        session = _make_session(_make_client(lambda _: httpx.Response(200)))
        session.close()
        with pytest.raises(Exception, match="closed"):
            session.exec("echo hi")


def _make_component(**config_kwargs: Any) -> CloudRunSandbox:
    """Builds a CloudRunSandbox without going through Stack/Client."""
    return CloudRunSandbox(
        name="test-cloudrun",
        id=uuid4(),
        config=CloudRunSandboxConfig(service_url=SERVICE_URL, **config_kwargs),
        flavor="cloudrun",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        environment={},
        secrets=[],
    )


class TestIdTokenCredentials:
    def test_unauthenticated_config_skips_credentials(self) -> None:
        component = _make_component(allow_unauthenticated=True)
        assert component._build_id_token_credentials() is None

    def test_service_account_credentials_converted(self) -> None:
        from google.oauth2 import service_account

        credentials = MagicMock(spec=service_account.Credentials)
        credentials.signer = MagicMock()
        credentials.service_account_email = "sa@project.iam"

        component = _make_component()
        with (
            patch.object(
                component,
                "_get_authentication",
                return_value=(credentials, "project"),
            ),
            patch.object(
                service_account, "IDTokenCredentials"
            ) as id_token_cls,
        ):
            component._build_id_token_credentials()

        assert id_token_cls.call_args.kwargs["target_audience"] == SERVICE_URL

    def test_unconvertible_connector_credentials_fail_loudly(self) -> None:
        """Connector creds that can't mint ID tokens must not silently
        fall back to the ambient ADC identity.
        """
        from google.oauth2.credentials import Credentials as UserCredentials

        component = _make_component()
        with (
            patch.object(
                component,
                "_get_authentication",
                return_value=(MagicMock(spec=UserCredentials), "project"),
            ),
            patch.object(component, "get_connector", return_value=MagicMock()),
        ):
            with pytest.raises(RuntimeError, match="cannot mint"):
                component._build_id_token_credentials()

    def test_unconvertible_service_account_path_fails_loudly(self) -> None:
        """An explicit service_account_path whose creds can't mint ID
        tokens must fail rather than fall back to ambient ADC.
        """
        from google.oauth2.credentials import Credentials as UserCredentials

        component = _make_component(
            service_account_path="/keys/service-account.json"
        )
        with (
            patch.object(
                component,
                "_get_authentication",
                return_value=(MagicMock(spec=UserCredentials), "project"),
            ),
            patch.object(component, "get_connector", return_value=None),
        ):
            with pytest.raises(RuntimeError, match="cannot mint"):
                component._build_id_token_credentials()


class TestComponentLifecycle:
    def test_create_session_cleans_up_on_failed_create(self) -> None:
        """A create that fails mid-flight must delete the sandbox by its
        caller-generated id so it can't orphan.
        """
        client = MagicMock()
        client.create_sandbox.side_effect = SandboxExecError("boom")
        component = _make_component()
        with patch.object(
            component, "_get_bridge_client", return_value=client
        ):
            with pytest.raises(SandboxExecError, match="boom"):
                component.create_session()
        created_id = client.create_sandbox.call_args.args[0]
        client.delete_sandbox.assert_called_once_with(created_id)

    def test_bridge_client_rebuilt_after_connector_expiry(self) -> None:
        component = _make_component()
        with (
            patch.object(
                component,
                "_build_id_token_credentials",
                return_value=None,
            ),
            patch.object(
                component, "connector_has_expired", return_value=False
            ),
        ):
            first = component._get_bridge_client()
            assert component._get_bridge_client() is first

        with (
            patch.object(
                component,
                "_build_id_token_credentials",
                return_value=None,
            ),
            patch.object(
                component, "connector_has_expired", return_value=True
            ),
        ):
            assert component._get_bridge_client() is not first
