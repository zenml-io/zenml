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
"""Cloud Run sandbox implementation backed by the sandbox bridge HTTP API.

Cloud Run sandboxes have no standalone REST API: the ``sandbox`` CLI only
exists inside a Cloud Run service deployed with ``--sandbox-launcher``. This
flavor therefore talks to a small "bridge" HTTP service (see
``examples/cloudrun_sandbox_bridge/``) deployed on such a service, using
Google-signed ID tokens for authentication — the standard Cloud Run IAM
invoker flow.
"""

import base64
import datetime
import json
import logging
import os
import posixpath
import shlex
import threading
import time
import urllib.parse
import uuid
from collections import deque
from dataclasses import dataclass
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    Union,
    cast,
)

import httpx

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp.flavors.cloudrun_sandbox_flavor import (
    DEFAULT_BRIDGE_TIMEOUT_MS,
    CloudRunSandboxConfig,
    CloudRunSandboxSettings,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
    SandboxSnapshot,
)
from zenml.utils.time_utils import exponential_backoff_delays, utc_now

logger = get_logger(__name__)

# Cloud Run caps non-streaming HTTP/1 request bodies at 32 MiB; the bridge
# inherits that limit for file transfer. Larger payloads should go through
# GCS and be pulled from inside the sandbox instead.
_BRIDGE_FILE_MAX_BYTES = 32 * 1024 * 1024

# Transient statuses worth retrying; 500s are bridge bugs and surface
# immediately.
_RETRYABLE_STATUSES: FrozenSet[int] = frozenset({429, 502, 503, 504})
# Only idempotent methods are retried: a POST that failed mid-flight may
# already have executed on the bridge (created a sandbox, launched a
# command), so retrying it risks double execution.
_RETRYABLE_METHODS: FrozenSet[str] = frozenset({"GET", "PUT", "DELETE"})
_MAX_RETRIES = 3

# Per-stream byte cap for the SSE pump buffers. A caller that only
# wait()s on a noisy command would otherwise grow these deques without
# bound; past the cap the oldest lines are dropped (logged once). The cap
# is on bytes, not line count, because the command is untrusted and can
# emit arbitrarily long (or newline-free) output to exhaust caller memory.
_STREAM_BUFFER_MAX_BYTES = 64 * 1024 * 1024
# A single newline-free run is flushed as a synthetic line past this size
# so the carried-over remainder (and its per-chunk copy) stays bounded.
_STREAM_REMAINDER_MAX_BYTES = 1_048_576

# Standard Google OAuth2 token endpoint, used when deriving ID-token
# credentials from plain service-account credentials.
_GOOGLE_OAUTH2_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Refresh ID tokens this many seconds before they expire so an exec that
# starts right at the boundary doesn't fail with a 401.
_TOKEN_REFRESH_SLACK_SECONDS = 60


class _IdTokenCredentials(Protocol):
    """Contract the bridge client needs from ID-token credentials.

    Satisfied structurally by ``google.oauth2.service_account
    .IDTokenCredentials``, ``google.auth.impersonated_credentials
    .IDTokenCredentials`` and ``_AdcIdTokenCredentials``.
    """

    token: Optional[str]

    @property
    def valid(self) -> bool:
        """Whether the cached token can still be used."""
        ...

    def refresh(self, request: Any) -> None:
        """Fetch a fresh token.

        Args:
            request: A ``google.auth.transport.Request`` instance.
        """
        ...


@dataclass(frozen=True)
class _BridgeEvent:
    """One decoded SSE event from the bridge exec stream."""

    # "stdout"/"stderr" events carry decoded text, "exit" carries the
    # exit code; error frames raise during parsing and never get here.
    kind: str
    data: Union[str, int]


def _sanitize_remote_path(remote_path: str) -> str:
    """Reject paths with `..` segments before they reach the bridge URL.

    Args:
        remote_path: A path inside the sandbox filesystem.

    Returns:
        The path stripped of any leading slash, ready for URL composition.

    Raises:
        ValueError: If the normalized path escapes the sandbox root.
    """
    stripped = remote_path.lstrip("/")
    normalized = posixpath.normpath(stripped)
    if normalized != stripped or normalized.split("/", 1)[0] == "..":
        raise ValueError(
            f"Remote path '{remote_path}' resolves outside the sandbox "
            "filesystem."
        )
    return stripped


def _parse_sse_stream(lines: Iterator[str]) -> Iterator[_BridgeEvent]:
    """Parse the bridge's text/event-stream into typed events.

    Args:
        lines: Decoded SSE lines (no trailing newlines).

    Yields:
        One ``_BridgeEvent`` per dispatch.
    """
    event: Optional[str] = None
    data_chunks: List[str] = []

    def _dispatch() -> Iterator[_BridgeEvent]:
        nonlocal event, data_chunks
        if event is None and not data_chunks:
            return
        raw_data = "\n".join(data_chunks)
        kind = event or "message"
        event = None
        data_chunks = []

        if kind == "stdout" or kind == "stderr":
            try:
                decoded = base64.b64decode(raw_data).decode(
                    "utf-8", errors="replace"
                )
            except Exception as e:
                raise SandboxExecError(
                    f"Malformed base64 on bridge '{kind}' frame: {e}"
                ) from e
            yield _BridgeEvent(kind=kind, data=decoded)
        elif kind == "exit":
            try:
                payload = json.loads(raw_data) if raw_data else {}
            except json.JSONDecodeError as e:
                raise SandboxExecError(
                    f"Malformed JSON on bridge 'exit' frame: {e}"
                ) from e
            if "exit_code" not in payload:
                # Missing exit_code is a protocol bug — surface it instead
                # of silently coercing to 0 (which would mask a failure).
                raise SandboxExecError(
                    f"Bridge 'exit' frame missing 'exit_code': {payload!r}"
                )
            yield _BridgeEvent(kind="exit", data=int(payload["exit_code"]))
        elif kind == "error":
            try:
                payload = json.loads(raw_data) if raw_data else {}
            except json.JSONDecodeError:
                payload = {"error": raw_data}
            raise SandboxExecError(
                f"Bridge exec error: {payload.get('error', payload)}"
            )
        # Unknown event kinds are ignored per SSE spec.

    for line in lines:
        if line == "":
            yield from _dispatch()
            continue

        if line.startswith(":"):
            # SSE comment / keep-alive.
            continue
        if line.startswith("event:"):
            event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            chunk = line[len("data:") :]
            if chunk.startswith(" "):
                chunk = chunk[1:]
            data_chunks.append(chunk)
        # Other field types ("id:", "retry:") are accepted but ignored.

    # Flush a trailing buffered event if the stream ended without a final
    # blank line. Without this, a bridge that closes the connection
    # right after writing `event: exit\ndata: ...\n` would silently lose
    # the exit frame and the caller would see exit_code=0.
    yield from _dispatch()


def _drain_sse_response(resp: "httpx.Response") -> Iterator[_BridgeEvent]:
    """Yield events from an already-open SSE response, closing it at the end.

    Args:
        resp: An open streaming ``httpx.Response``.

    Yields:
        Each decoded ``_BridgeEvent`` from the response body.
    """
    try:
        yield from _parse_sse_stream(resp.iter_lines())
    finally:
        try:
            resp.close()
        except Exception:
            logger.debug("Closing bridge SSE response failed", exc_info=True)


class _AdcIdTokenCredentials:
    """ID-token credentials minted via ``google.oauth2.id_token``.

    Fallback for credential types with no native ID-token counterpart
    (e.g. plain Application Default Credentials on a workstation or the
    metadata server on GCE/Cloud Run). Mimics the small slice of the
    ``google.auth.credentials.Credentials`` surface the bridge client
    uses: ``valid``, ``token`` and ``refresh()``.
    """

    def __init__(self, audience: str) -> None:
        """Initialize the credentials.

        Args:
            audience: The audience claim for minted ID tokens.
        """
        self._audience = audience
        self.token: Optional[str] = None
        self.expiry: Optional[datetime.datetime] = None

    @property
    def valid(self) -> bool:
        """Whether the cached token is present and not about to expire.

        Returns:
            ``True`` if the token can still be used.
        """
        if self.token is None or self.expiry is None:
            return False
        remaining = self.expiry - utc_now(tz_aware=True)
        return remaining.total_seconds() > _TOKEN_REFRESH_SLACK_SECONDS

    def refresh(self, request: Any) -> None:
        """Fetch a fresh ID token via the ADC-based helper.

        Args:
            request: A ``google.auth.transport.Request`` instance.

        Raises:
            RuntimeError: If the ambient credentials cannot mint ID tokens.
        """
        from google.auth import exceptions as google_auth_exceptions
        from google.auth import jwt as google_jwt
        from google.oauth2 import id_token as google_id_token

        try:
            token = google_id_token.fetch_id_token(request, self._audience)
        except google_auth_exceptions.GoogleAuthError as e:
            raise RuntimeError(
                "Could not mint a Google ID token for the Cloud Run "
                f"sandbox bridge (audience '{self._audience}'): {e}. ID "
                "tokens require service-account credentials: link a GCP "
                "service connector, set service_account_path on the "
                "sandbox component, or run with service-account-based "
                "Application Default Credentials. User credentials from "
                "`gcloud auth application-default login` cannot mint ID "
                "tokens."
            ) from e
        claims = google_jwt.decode(token, verify=False)
        self.token = token
        self.expiry = datetime.datetime.fromtimestamp(
            int(claims["exp"]), tz=datetime.timezone.utc
        )


class _CloudRunBridgeClient:
    """HTTP wrapper around the bridge's /v1/sandbox/* surface."""

    def __init__(
        self,
        service_url: str,
        credentials: Optional[_IdTokenCredentials],
        *,
        transport: Optional["httpx.BaseTransport"] = None,
    ) -> None:
        """Initialize the client.

        Args:
            service_url: Base URL of the deployed bridge service.
            credentials: Google ID-token credentials used to authorize
                requests (``None`` for unauthenticated bridges).
            transport: Optional httpx transport override, used by tests.
        """
        self._credentials = credentials
        self._credentials_lock = threading.Lock()
        # Reused across token refreshes: each google transport Request
        # wraps its own requests.Session, so rebuilding it per refresh
        # would pay a fresh TLS handshake to the token endpoint.
        self._auth_transport: Optional[Any] = None
        # SSE exec streams disable the read timeout per-request; plain
        # calls keep the default so a hung bridge can't block forever.
        self._client = httpx.Client(
            base_url=service_url.rstrip("/"),
            timeout=httpx.Timeout(30.0),
            transport=transport,
        )

    def close(self) -> None:
        """Release the underlying HTTP client."""
        try:
            self._client.close()
        except Exception:
            logger.debug("Closing bridge HTTP client failed", exc_info=True)

    def _auth_headers(self) -> Dict[str, str]:
        """Build the Authorization header from the ID-token credentials.

        Returns:
            Headers to merge into the outgoing request.
        """
        credentials = self._credentials
        if credentials is None:
            return {}
        # Optimistic fast path: only serialize the refresh itself, so
        # concurrent requests holding a still-valid token don't contend.
        if not credentials.valid:
            with self._credentials_lock:
                if not credentials.valid:
                    if self._auth_transport is None:
                        from google.auth.transport.requests import Request

                        self._auth_transport = Request()
                    credentials.refresh(self._auth_transport)
        return {"Authorization": f"Bearer {credentials.token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        ok_statuses: Tuple[int, ...] = (),
    ) -> "httpx.Response":
        """Issue a request with the bridge's retry policy.

        Args:
            method: HTTP verb.
            path: Path under the bridge base URL.
            json_body: JSON body for write requests.
            content: Raw bytes body (mutually exclusive with json_body).
            headers: Extra headers.
            stream: When True, return the response without reading it.
            ok_statuses: Error statuses that carry meaning for the caller
                (e.g. a 404 that answers a liveness probe); returned
                as-is instead of raising or retrying.

        Returns:
            The httpx Response.

        Raises:
            SandboxExecError: On a non-retryable error, or after retries
                are exhausted.
        """
        retryable_method = method in _RETRYABLE_METHODS
        delays = exponential_backoff_delays(
            attempts=_MAX_RETRIES, initial_delay=0.25, max_delay=8.0
        )
        while True:
            merged_headers = dict(headers or {})
            merged_headers.update(self._auth_headers())
            cause: Optional[BaseException] = None
            retryable = retryable_method
            try:
                if stream:
                    req = self._client.build_request(
                        method,
                        path,
                        json=json_body,
                        content=content,
                        headers=merged_headers,
                        timeout=httpx.Timeout(30.0, read=None),
                    )
                    resp = self._client.send(req, stream=True)
                else:
                    resp = self._client.request(
                        method,
                        path,
                        json=json_body,
                        content=content,
                        headers=merged_headers,
                    )
            except httpx.HTTPError as e:
                cause = e
                error_message = f"Bridge request {method} {path} failed: {e}"
            else:
                if resp.status_code in ok_statuses or resp.status_code < 400:
                    return resp

                retryable = (
                    retryable_method
                    and resp.status_code in _RETRYABLE_STATUSES
                )
                body_preview = ""
                if not stream:
                    try:
                        body_preview = resp.text[:500]
                    except Exception:
                        body_preview = ""
                else:
                    try:
                        resp.close()
                    except Exception:
                        pass
                error_message = (
                    f"Bridge {method} {path} returned "
                    f"{resp.status_code}: {body_preview}"
                )

            delay = next(delays, None) if retryable else None
            if delay is None:
                raise SandboxExecError(error_message) from cause
            time.sleep(delay)

    def create_sandbox(
        self,
        sandbox_id: str,
        *,
        allow_egress: bool = False,
        import_tar_uri: Optional[str] = None,
    ) -> None:
        """Create a sandbox on the bridge instance under a caller-chosen id.

        The caller generates the id and the bridge creation is idempotent,
        so a create whose response is lost cannot orphan the sandbox: the
        caller still knows the id and can delete it.

        Args:
            sandbox_id: The caller-generated sandbox id.
            allow_egress: Whether the sandbox gets outbound network access.
            import_tar_uri: Optional ``gs://`` URI of a filesystem snapshot
                tarball to initialize the sandbox from.
        """
        body: Dict[str, Any] = {
            "id": sandbox_id,
            "allow_egress": allow_egress,
        }
        if import_tar_uri is not None:
            body["import_tar_uri"] = import_tar_uri
        self._request("POST", "/v1/sandbox", json_body=body)

    def delete_sandbox(self, sandbox_id: str) -> None:
        """Delete a sandbox.

        Args:
            sandbox_id: The sandbox to delete.
        """
        self._request(
            "DELETE", f"/v1/sandbox/{sandbox_id}", ok_statuses=(404, 410)
        )

    def is_running(self, sandbox_id: str) -> bool:
        """Check whether the given sandbox is still alive.

        Args:
            sandbox_id: The sandbox to check.

        Returns:
            True if the bridge reports the sandbox as running, False if it
            reports it as stopped or unknown (404/410).
        """
        resp = self._request(
            "GET",
            f"/v1/sandbox/{sandbox_id}/running",
            ok_statuses=(404, 410),
        )
        if resp.status_code in (404, 410):
            return False
        return bool(resp.json().get("running", False))

    def snapshot_sandbox(self, sandbox_id: str, gcs_uri: str) -> None:
        """Export the sandbox filesystem overlay to Cloud Storage.

        The bridge writes the tarball to exactly the URI it is given, so
        a successful response needs no payload.

        Args:
            sandbox_id: The sandbox to snapshot.
            gcs_uri: Destination ``gs://`` URI for the tarball.
        """
        self._request(
            "POST",
            f"/v1/sandbox/{sandbox_id}/snapshot",
            json_body={"gcs_uri": gcs_uri},
        )

    def exec_stream(
        self,
        sandbox_id: str,
        argv: List[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_ms: int = DEFAULT_BRIDGE_TIMEOUT_MS,
        exec_id: Optional[str] = None,
    ) -> Tuple["httpx.Response", Iterator[_BridgeEvent]]:
        """Run a command and stream decoded SSE events.

        Args:
            sandbox_id: The sandbox to exec into.
            argv: Command argv list.
            cwd: Optional working directory.
            env: Environment variables for this command (passed to the
                ``sandbox`` CLI via ``--env``; sandboxes inherit nothing
                from the host).
            timeout_ms: Per-exec timeout in milliseconds.
            exec_id: Caller-generated id under which the bridge registers
                the running command, so ``kill_exec`` can terminate it.

        Returns:
            The open streaming response (closing it aborts the stream and
            unblocks a reader mid-iteration) and an iterator of
            ``_BridgeEvent`` instances in dispatch order.
        """
        body: Dict[str, Any] = {"argv": argv, "timeout_ms": timeout_ms}
        if cwd is not None:
            body["cwd"] = cwd
        if env:
            body["env"] = env
        if exec_id is not None:
            body["exec_id"] = exec_id

        # POST eagerly so 4xx/auth errors raise at the call site; only SSE
        # decoding is deferred.
        resp = self._request(
            "POST",
            f"/v1/sandbox/{sandbox_id}/exec",
            json_body=body,
            stream=True,
        )
        return resp, _drain_sse_response(resp)

    def kill_exec(self, sandbox_id: str, exec_id: str) -> None:
        """Ask the bridge to terminate a running command.

        Args:
            sandbox_id: The sandbox the command runs in.
            exec_id: The id passed to ``exec_stream`` for the command.
        """
        self._request(
            "DELETE",
            f"/v1/sandbox/{sandbox_id}/exec/{exec_id}",
            ok_statuses=(404, 410),
        )

    def put_file(self, sandbox_id: str, remote_path: str, data: bytes) -> None:
        """Upload raw bytes to a sandbox path.

        Size enforcement lives in ``_upload_file`` (the only caller),
        which checks before reading the payload into memory.

        Args:
            sandbox_id: The sandbox to write into.
            remote_path: Path inside the sandbox filesystem; `..` rejected.
            data: Raw file bytes; max 32 MiB.
        """
        safe_path = _sanitize_remote_path(remote_path)
        encoded = urllib.parse.quote(safe_path, safe="/")
        self._request(
            "PUT",
            f"/v1/sandbox/{sandbox_id}/file/{encoded}",
            content=data,
            headers={"Content-Type": "application/octet-stream"},
        )

    def get_file(self, sandbox_id: str, remote_path: str) -> bytes:
        """Download raw bytes from a sandbox path.

        Args:
            sandbox_id: The sandbox to read from.
            remote_path: Path inside the sandbox filesystem.

        Returns:
            The raw file contents (bridge caps at 32 MiB).
        """
        safe_path = _sanitize_remote_path(remote_path)
        encoded = urllib.parse.quote(safe_path, safe="/")
        resp = self._request("GET", f"/v1/sandbox/{sandbox_id}/file/{encoded}")
        return resp.content


class CloudRunSandboxProcess(SandboxProcess):
    """Demuxes a single SSE event iterator into stdout / stderr / exit."""

    def __init__(
        self,
        event_iter: Iterator[_BridgeEvent],
        *,
        session: "CloudRunSandboxSession",
        started_at: float,
        response: Optional["httpx.Response"] = None,
        client: Optional["_CloudRunBridgeClient"] = None,
        sandbox_id: Optional[str] = None,
        exec_id: Optional[str] = None,
    ) -> None:
        """Initialize the process wrapper.

        Args:
            event_iter: Iterator yielding bridge SSE events for this exec.
            session: Owning session.
            started_at: Wall-clock launch time.
            response: The underlying streaming SSE response; ``kill()``
                closes it to unblock the pump thread mid-read.
            client: Bridge client used by ``kill()`` to terminate the
                remote command.
            sandbox_id: The sandbox the command runs in.
            exec_id: The bridge exec id used by ``kill()``.
        """
        super().__init__(session=session, started_at=started_at)
        self._event_iter = event_iter
        self._response = response
        self._client = client
        self._sandbox_id = sandbox_id
        self._exec_id = exec_id
        self._killed = threading.Event()

        # The bridge multiplexes stdout/stderr on one SSE stream. We pump
        # it once on a background thread and demux into two buffers so
        # `stdout()` and `stderr()` can be iterated independently from the
        # caller's thread.
        self._stdout_buf: Deque[str] = deque()
        self._stderr_buf: Deque[str] = deque()
        self._buffered_bytes: Dict[str, int] = {"stdout": 0, "stderr": 0}
        self._buffer_truncated = False
        self._data_available = threading.Condition()
        self._done = threading.Event()
        self._exit_code: Optional[int] = None
        self._pump_error: Optional[BaseException] = None
        self._stdout_remainder = ""
        self._stderr_remainder = ""

        self._pump = threading.Thread(
            target=self._pump_events,
            name="cloudrun-bridge-pump",
            daemon=True,
        )
        self._pump.start()

    def _enqueue(self, stream: str, target: Deque[str], chunk: str) -> None:
        """Append a chunk, dropping oldest data once the byte cap is hit.

        Callers hold ``self._data_available``.

        Args:
            stream: ``"stdout"`` or ``"stderr"`` — selects the byte counter.
            target: Buffer to append to.
            chunk: The text to append.
        """
        target.append(chunk)
        self._buffered_bytes[stream] += len(chunk)
        while (
            self._buffered_bytes[stream] > _STREAM_BUFFER_MAX_BYTES
            and len(target) > 1
        ):
            dropped = target.popleft()
            self._buffered_bytes[stream] -= len(dropped)
            if not self._buffer_truncated:
                self._buffer_truncated = True
                logger.warning(
                    "Cloud Run exec output exceeded the %d-byte per-stream "
                    "buffer; oldest undrained output is being dropped. "
                    "Drain process.stdout()/stderr() (or use collect()) to "
                    "keep full output.",
                    _STREAM_BUFFER_MAX_BYTES,
                )

    def _push_text(
        self, stream: str, target: Deque[str], remainder: str, text: str
    ) -> str:
        """Line-buffer arbitrary text into the target deque.

        Args:
            stream: ``"stdout"`` or ``"stderr"``.
            target: Buffer to append lines to.
            remainder: Partial line carried over from the previous chunk.
            text: New text chunk.

        Returns:
            The trailing partial line (no newline yet) to carry over.
        """
        buf = remainder + text
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            self._enqueue(stream, target, line + "\n")
        # Newline-free output would otherwise grow the remainder (and the
        # per-chunk `remainder + text` copy) without bound; flush it as a
        # synthetic line past the cap.
        if len(buf) > _STREAM_REMAINDER_MAX_BYTES:
            self._enqueue(stream, target, buf)
            return ""
        return buf

    def _flush_remainders(self) -> None:
        """Push trailing partial lines (no terminating newline) on stream end."""
        if self._stdout_remainder:
            self._enqueue("stdout", self._stdout_buf, self._stdout_remainder)
            self._stdout_remainder = ""
        if self._stderr_remainder:
            self._enqueue("stderr", self._stderr_buf, self._stderr_remainder)
            self._stderr_remainder = ""

    def _pump_events(self) -> None:
        """Background pump: drain SSE iterator into stdout/stderr buffers."""
        try:
            for ev in self._event_iter:
                with self._data_available:
                    if ev.kind == "exit":
                        self._exit_code = int(ev.data)
                    elif ev.kind == "stdout":
                        self._stdout_remainder = self._push_text(
                            "stdout",
                            self._stdout_buf,
                            self._stdout_remainder,
                            cast(str, ev.data),
                        )
                    elif ev.kind == "stderr":
                        self._stderr_remainder = self._push_text(
                            "stderr",
                            self._stderr_buf,
                            self._stderr_remainder,
                            cast(str, ev.data),
                        )
                    self._data_available.notify_all()
        except BaseException as e:  # noqa: BLE001
            # kill() closes the response under our feet; the resulting
            # httpx error is the expected shutdown path, not a failure.
            if not self._killed.is_set():
                self._pump_error = e
        finally:
            with self._data_available:
                self._flush_remainders()
                self._done.set()
                self._data_available.notify_all()

    def _iter_buffer(self, stream: str, buf: Deque[str]) -> Iterator[str]:
        """Block-pop lines from a buffer until the pump signals done.

        Args:
            stream: ``"stdout"`` or ``"stderr"`` — selects the byte counter.
            buf: The buffer to drain.

        Yields:
            One line per call.
        """
        while True:
            with self._data_available:
                while not buf and not self._done.is_set():
                    self._data_available.wait()
                if buf:
                    line = buf.popleft()
                    self._buffered_bytes[stream] -= len(line)
                else:
                    return
            yield line

    def stdout(self) -> Iterator[str]:
        """Yields stdout lines, routed through the session log source.

        Returns:
            Line iterator wrapped via ``session._wrap_stream`` so each line
            also lands in the per-session ``sandbox:<id>`` log.
        """
        return self._session._wrap_stream(
            self._iter_buffer("stdout", self._stdout_buf),
            log_level=logging.INFO,
        )

    def stderr(self) -> Iterator[str]:
        """Yields stderr lines, routed through the session log source.

        Returns:
            Line iterator wrapped via ``session._wrap_stream`` so each line
            also lands in the per-session ``sandbox:<id>`` log.
        """
        return self._session._wrap_stream(
            self._iter_buffer("stderr", self._stderr_buf),
            log_level=logging.ERROR,
        )

    def wait(self, timeout: Optional[float] = None) -> int:
        """Block until the process exits, or ``timeout`` seconds pass.

        Args:
            timeout: Optional wall-clock cap. ``None`` waits indefinitely.

        Returns:
            The exit code captured from the bridge.

        Raises:
            TimeoutError: If ``timeout`` elapsed before the bridge sent an
                ``exit`` frame.
            SandboxExecError: If the pump captured an error, the stream was
                killed via ``kill()``/``close()``, or it ended without an
                exit frame.
        """
        completed = self._done.wait(timeout)
        if not completed:
            raise TimeoutError(
                f"Cloud Run exec did not complete within {timeout}s. "
                "Call process.kill() or session.destroy() to release the "
                "bridge stream."
            )
        pump_err = self._pump_error
        if pump_err is not None:
            message = (
                str(pump_err)
                if isinstance(pump_err, SandboxExecError)
                else f"Bridge SSE pump failed: {pump_err}"
            )
            raise SandboxExecError(message) from pump_err
        if self._exit_code is None:
            if self._killed.is_set():
                raise SandboxExecError(
                    "exec stream was killed via kill() or session close(); "
                    "the bridge was asked to terminate the command, but its "
                    "exit status was not observed"
                )
            # Stream ended cleanly but no exit frame arrived (truncated
            # SSE, bridge stalled out, Cloud Run request timeout hit).
            # Surface this as a failure rather than returning a bogus 0.
            raise SandboxExecError(
                "Cloud Run exec finished without an exit frame; the bridge "
                "stream may have been truncated by the Cloud Run request "
                "timeout or stalled."
            )
        return self._exit_code

    def kill(self) -> None:
        """Terminate the remote command and stop reading its stream."""
        # Set the flag before closing so the pump treats the resulting
        # httpx error as a clean shutdown.
        self._killed.set()
        # Terminate the command on the bridge first; closing the local
        # response alone would leave it running until timeout_ms.
        if (
            self._client is not None
            and self._sandbox_id is not None
            and self._exec_id is not None
        ):
            try:
                self._client.kill_exec(self._sandbox_id, self._exec_id)
            except Exception:
                logger.debug(
                    "Bridge kill request for exec %s failed",
                    self._exec_id,
                    exc_info=True,
                )
        if self._response is not None:
            try:
                self._response.close()
            except Exception:
                logger.debug(
                    "Closing bridge SSE response during kill() failed",
                    exc_info=True,
                )
        with self._data_available:
            self._done.set()
            self._data_available.notify_all()

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or ``None`` while still running.

        Returns:
            The captured exit code or ``None``.
        """
        return self._exit_code


class CloudRunSandboxSession(SandboxSession):
    """Cloud Run sandbox session over the bridge HTTP API."""

    def __init__(
        self,
        sandbox_id: str,
        *,
        client: _CloudRunBridgeClient,
        parent: "CloudRunSandbox",
        session_env: Optional[Dict[str, str]] = None,
        default_cwd: Optional[str] = None,
        default_timeout_ms: int = DEFAULT_BRIDGE_TIMEOUT_MS,
        snapshot_uri_prefix: Optional[str] = None,
        destroy_on_exit: bool = False,
    ) -> None:
        """Initialize the session.

        Args:
            sandbox_id: The bridge-assigned sandbox id (used as session id).
            client: Bridge HTTP client.
            parent: Owning sandbox component.
            session_env: Env vars merged into every exec. Cloud Run
                sandboxes inherit nothing from the host, and the bridge
                keeps no session state, so the client resends these on
                each command.
            default_cwd: Default working directory for execs.
            default_timeout_ms: Default per-exec timeout in milliseconds.
            snapshot_uri_prefix: ``gs://`` prefix for snapshot tarballs;
                ``None`` disables snapshot support.
            destroy_on_exit: Whether the context manager destroys the
                sandbox on exit instead of just closing the handle.
        """
        # Subclass state must be set before super().__init__, which
        # publishes session metadata during construction.
        self._client = client
        self._sandbox_id = sandbox_id
        self._session_env = dict(session_env or {})
        self._default_cwd = default_cwd
        self._default_timeout_ms = default_timeout_ms
        self._snapshot_uri_prefix = snapshot_uri_prefix
        self._processes: List[CloudRunSandboxProcess] = []
        super().__init__(
            id=sandbox_id, parent=parent, destroy_on_exit=destroy_on_exit
        )

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Launch a command in the sandbox.

        Args:
            command: A list (argv) or string (shell-split via
                ``shlex.split``).
            cwd: Working directory inside the sandbox.
            env: Per-exec environment variables, merged over the
                session-level ``sandbox_environment``. The bridge passes
                them to the ``sandbox`` CLI as ``--env`` flags, so they do
                not appear on the sandboxed process's own command line
                (they are still visible in the trusted bridge host's
                process list).

        Returns:
            A ``CloudRunSandboxProcess``.
        """
        argv: List[str] = (
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        self._log_command(argv)

        # Prune exited processes: a long-lived session running thousands
        # of execs would otherwise retain every finished process and its
        # output buffers until close().
        self._processes = [p for p in self._processes if p.exit_code is None]

        merged_env = {**self._session_env, **(env or {})}
        effective_cwd = cwd if cwd is not None else self._default_cwd
        exec_id = uuid.uuid4().hex
        started_at = time.time()
        # exec_stream surfaces every failure mode as SandboxExecError, so
        # launch errors propagate to the caller as-is.
        response, event_iter = self._client.exec_stream(
            self._sandbox_id,
            argv,
            cwd=effective_cwd,
            env=merged_env or None,
            timeout_ms=self._default_timeout_ms,
            exec_id=exec_id,
        )
        process = CloudRunSandboxProcess(
            event_iter,
            session=self,
            started_at=started_at,
            response=response,
            client=self._client,
            sandbox_id=self._sandbox_id,
            exec_id=exec_id,
        )
        self._processes.append(process)
        return process

    def _create_snapshot(self) -> SandboxSnapshot:
        """Export the sandbox filesystem overlay to Cloud Storage.

        Returns:
            A ``SandboxSnapshot`` whose ``ref`` is the ``gs://`` URI of the
            tarball produced by ``sandbox tar`` on the bridge. Only
            filesystem state is captured — running processes and
            environment variables are not part of the snapshot.

        Raises:
            NotImplementedError: If the component has no
                ``snapshot_uri_prefix`` configured.
        """
        if not self._snapshot_uri_prefix:
            raise NotImplementedError(
                "Snapshots require the 'snapshot_uri_prefix' config "
                "attribute on the Cloud Run sandbox component (a gs:// "
                "location the bridge service account can write to)."
            )
        # Include a uuid so two snapshots of one sandbox within the same
        # second get distinct object names instead of overwriting each
        # other (which would silently change what the first restores).
        gcs_uri = (
            f"{self._snapshot_uri_prefix}/{self._sandbox_id}-"
            f"{int(time.time())}-{uuid.uuid4().hex[:8]}.tar"
        )
        self._client.snapshot_sandbox(self._sandbox_id, gcs_uri)
        return SandboxSnapshot(
            sandbox_id=self._parent.id,
            ref=gcs_uri,
            metadata={"source_sandbox": self._sandbox_id},
        )

    def _resolve_remote_path(self, remote_path: str) -> str:
        """Resolve a relative remote path against the session's default cwd.

        The base contract documented on ``SandboxSession.upload_file`` /
        ``download_file`` specifies that a relative ``remote_path``
        resolves against the session's working directory — the same
        directory ``exec()`` uses as its default cwd. Without this,
        ``exec`` and file transfer disagree about where a relative path
        lives: ``exec`` honors ``default_cwd`` while the bridge anchors
        relative file paths at the sandbox root.

        Absolute paths and the no-configured-cwd case are returned
        unchanged; the client's ``_sanitize_remote_path`` still rejects
        any result that escapes the sandbox root (e.g. a relative
        ``../`` that climbs above ``default_cwd``).

        Args:
            remote_path: The caller-supplied destination/source path.

        Returns:
            The joined absolute path when a default cwd is configured and
            the input is relative; otherwise the path unchanged.
        """
        if self._default_cwd and not posixpath.isabs(remote_path):
            return posixpath.join(self._default_cwd, remote_path)
        return remote_path

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file into the sandbox.

        Args:
            local_path: Source path on the caller's machine.
            remote_path: Destination path inside the sandbox filesystem.
                Relative paths resolve against the session's default cwd.

        Raises:
            ValueError: If the file exceeds the bridge's body limit.
        """
        # Check the size before reading: loading an oversized file into
        # memory just to have put_file reject it invites an OOM.
        size = os.path.getsize(local_path)
        if size > _BRIDGE_FILE_MAX_BYTES:
            raise ValueError(
                f"File '{local_path}' is {size} bytes, exceeding the "
                f"bridge's {_BRIDGE_FILE_MAX_BYTES}-byte upload limit."
            )
        with open(local_path, "rb") as f:
            data = f.read()
        self._client.put_file(
            self._sandbox_id, self._resolve_remote_path(remote_path), data
        )

    def _download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the sandbox.

        Args:
            remote_path: Source path inside the sandbox filesystem.
                Relative paths resolve against the session's default cwd.
            local_path: Destination path on the caller's machine.
        """
        data = self._client.get_file(
            self._sandbox_id, self._resolve_remote_path(remote_path)
        )
        with open(local_path, "wb") as f:
            f.write(data)

    def _close(self) -> None:
        """Release local exec streams; the sandbox keeps running."""
        for process in self._processes:
            if process.exit_code is None:
                process.kill()

    def _destroy(self) -> None:
        """Terminate the sandbox on the bridge instance.

        Raises:
            RuntimeError: If the bridge fails to delete the sandbox.
        """
        try:
            self._client.delete_sandbox(self._sandbox_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to delete Cloud Run sandbox '{self._sandbox_id}': "
                f"{e}. It keeps consuming the bridge instance's resources "
                "until deleted or the instance is recycled; retry "
                "destroy() to terminate it."
            ) from e


class CloudRunSandbox(BaseSandbox, GoogleCredentialsMixin):
    """Sandbox flavor backed by Cloud Run sandboxes via a bridge service."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Cloud Run sandbox component.

        Args:
            *args: Forwarded to ``StackComponent``.
            **kwargs: Forwarded to ``StackComponent``.
        """
        super().__init__(*args, **kwargs)
        self._bridge_client: Optional[_CloudRunBridgeClient] = None
        self._bridge_client_lock = threading.Lock()

    @property
    def config(self) -> CloudRunSandboxConfig:
        """Typed config.

        Returns:
            The Cloud-Run-specific config.
        """
        return cast(CloudRunSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class.

        Returns:
            ``CloudRunSandboxSettings``.
        """
        return CloudRunSandboxSettings

    def _build_id_token_credentials(
        self,
    ) -> Optional[_IdTokenCredentials]:
        """Derive ID-token credentials for the bridge from the GCP auth.

        Cloud Run IAM authenticates callers with Google-signed ID tokens
        (not OAuth2 access tokens), so the component's credentials — from
        a linked GCP service connector, a service-account key file, or
        Application Default Credentials — must be converted to an
        ID-token-minting counterpart.

        Returns:
            Credentials exposing ``valid``/``token``/``refresh``, or
            ``None`` when ``allow_unauthenticated`` is set.

        Raises:
            RuntimeError: If a linked service connector uses an auth method
                whose credentials cannot mint ID tokens (user account,
                OAuth2 token, external account).
        """
        if self.config.allow_unauthenticated:
            return None

        from google.auth import impersonated_credentials
        from google.oauth2 import service_account

        audience = self.config.audience or self.config.service_url
        credentials, _ = self._get_authentication()

        if isinstance(credentials, impersonated_credentials.Credentials):
            return cast(
                _IdTokenCredentials,
                impersonated_credentials.IDTokenCredentials(
                    credentials,
                    target_audience=audience,
                    include_email=True,
                ),
            )
        if isinstance(credentials, service_account.Credentials):
            return cast(
                _IdTokenCredentials,
                service_account.IDTokenCredentials(
                    signer=credentials.signer,
                    service_account_email=credentials.service_account_email,
                    token_uri=_GOOGLE_OAUTH2_TOKEN_ENDPOINT,
                    target_audience=audience,
                ),
            )
        if (
            self.get_connector() is not None
            or self.config.service_account_path
        ):
            # An explicitly-chosen credential source (connector or
            # service_account_path) produced credentials we can't convert
            # (user account, OAuth2 token, external account). Falling back
            # to the ambient-ADC helper below would ignore that choice and
            # silently authenticate to the bridge as a *different identity*
            # (e.g. the metadata server) — fail loudly instead.
            raise RuntimeError(
                f"The configured GCP credentials ({type(credentials).__name__}) "
                "cannot mint the Google ID tokens Cloud Run IAM requires. "
                "Use a service-account or impersonation service connector, a "
                "service-account JSON key at service_account_path, or "
                "service-account-based Application Default Credentials."
            )
        # Plain ADC (workstation or metadata server): fall back to the
        # generic fetch_id_token helper, which raises a clear error for
        # credential types that cannot mint ID tokens (e.g. user creds).
        return _AdcIdTokenCredentials(audience)

    def _get_bridge_client(self) -> _CloudRunBridgeClient:
        """Return the lazily-built bridge HTTP client.

        Rebuilds the client (and its baked-in ID-token credentials) once
        the linked service connector has expired, so a component does not
        keep signing tokens with credentials the connector no longer
        vouches for.

        Returns:
            A cached ``_CloudRunBridgeClient`` bound to this component.
        """
        with self._bridge_client_lock:
            if (
                self._bridge_client is not None
                and self.connector_has_expired()
            ):
                self._bridge_client.close()
                self._bridge_client = None
            if self._bridge_client is None:
                self._bridge_client = _CloudRunBridgeClient(
                    self.config.service_url,
                    self._build_id_token_credentials(),
                )
            return self._bridge_client

    def _build_session(
        self,
        sandbox_id: str,
        settings: CloudRunSandboxSettings,
        destroy_on_exit: bool = False,
    ) -> CloudRunSandboxSession:
        """Construct a session handle for an existing sandbox.

        Args:
            sandbox_id: The bridge-assigned sandbox id.
            settings: Resolved settings for the session.
            destroy_on_exit: Whether the session context manager destroys
                the sandbox on exit.

        Returns:
            A ``CloudRunSandboxSession``.
        """
        return CloudRunSandboxSession(
            sandbox_id,
            client=self._get_bridge_client(),
            parent=self,
            session_env=self._resolve_session_environment(settings),
            default_cwd=settings.cwd,
            default_timeout_ms=settings.timeout_ms,
            snapshot_uri_prefix=self.config.snapshot_uri_prefix,
            destroy_on_exit=destroy_on_exit,
        )

    def create_session(
        self,
        settings: Optional[BaseSandboxSettings] = None,
        destroy_on_exit: bool = False,
    ) -> SandboxSession:
        """Boot a fresh Cloud Run sandbox via the bridge.

        Args:
            settings: Optional per-step overrides.
            destroy_on_exit: Whether to destroy the sandbox session when
                the session context manager exits.

        Returns:
            A ``CloudRunSandboxSession`` bound to the new sandbox.
        """
        eff = cast(CloudRunSandboxSettings, self.resolve_settings(settings))
        sandbox_id = self._new_sandbox_id()
        client = self._get_bridge_client()
        self._create_sandbox_or_cleanup(
            client, sandbox_id, allow_egress=eff.allow_egress
        )
        return self._build_session(
            sandbox_id, eff, destroy_on_exit=destroy_on_exit
        )

    def attach(self, session_id: str) -> SandboxSession:
        """Reattach to a still-running Cloud Run sandbox by id.

        Persistent sandboxes only survive as long as the bridge instance
        that owns them, so attaching fails when Cloud Run has recycled the
        instance in the meantime.

        Args:
            session_id: The bridge sandbox id to attach to.

        Returns:
            A ``CloudRunSandboxSession``.

        Raises:
            RuntimeError: If the bridge reports the sandbox as not running.
        """
        if not self._get_bridge_client().is_running(session_id):
            raise RuntimeError(
                f"Cloud Run sandbox '{session_id}' is not running. The "
                "bridge instance that owned it may have been recycled; "
                "create a new session (optionally from a snapshot)."
            )
        eff = cast(CloudRunSandboxSettings, self.resolve_settings(None))
        return self._build_session(session_id, eff)

    def restore(self, snapshot: SandboxSnapshot) -> SandboxSession:
        """Boot a new sandbox from a stored filesystem snapshot.

        Args:
            snapshot: A ``SandboxSnapshot`` whose ``ref`` is a ``gs://``
                tarball URI captured via ``create_snapshot()``.

        Returns:
            A new ``CloudRunSandboxSession`` initialized from the tarball.
            No in-memory state from the original session is preserved, and
            env vars are re-applied from the resolved settings.
        """
        self._validate_snapshot(snapshot)
        eff = cast(CloudRunSandboxSettings, self.resolve_settings(None))
        sandbox_id = self._new_sandbox_id()
        client = self._get_bridge_client()
        self._create_sandbox_or_cleanup(
            client,
            sandbox_id,
            allow_egress=eff.allow_egress,
            import_tar_uri=snapshot.ref,
        )
        return self._build_session(sandbox_id, eff)

    @staticmethod
    def _new_sandbox_id() -> str:
        """Generate a fresh sandbox id.

        Returns:
            An id of the form ``sb-<12 hex chars>``.
        """
        return f"sb-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _create_sandbox_or_cleanup(
        client: "_CloudRunBridgeClient",
        sandbox_id: str,
        *,
        allow_egress: bool = False,
        import_tar_uri: Optional[str] = None,
    ) -> None:
        """Create a sandbox, deleting it if the create fails mid-flight.

        Because the id is caller-generated, a create whose response is lost
        (the bridge may have created the sandbox before the connection
        dropped) can still be cleaned up here instead of orphaning a
        ``sleep infinity`` process on the bridge instance.

        Args:
            client: Bridge client.
            sandbox_id: The caller-generated sandbox id.
            allow_egress: Whether the sandbox gets outbound network access.
            import_tar_uri: Optional ``gs://`` snapshot tarball to boot from.

        Raises:
            Exception: Re-raises whatever the create call raised, after a
                best-effort delete of the possibly-created sandbox.
        """
        try:
            client.create_sandbox(
                sandbox_id,
                allow_egress=allow_egress,
                import_tar_uri=import_tar_uri,
            )
        except Exception:
            try:
                client.delete_sandbox(sandbox_id)
            except Exception:
                logger.warning(
                    "Failed to clean up sandbox %s after a failed create; "
                    "it may linger until the bridge instance is recycled.",
                    sandbox_id,
                )
            raise
