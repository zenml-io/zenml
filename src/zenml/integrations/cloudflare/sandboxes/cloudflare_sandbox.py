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
"""Cloudflare sandbox implementation backed by the bridge HTTP API."""

import base64
import json
import logging
import os
import posixpath
import shlex
import threading
import time
import urllib.parse
from collections import deque
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Deque,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from zenml.config.base_settings import BaseSettings
from zenml.integrations.cloudflare.flavors.cloudflare_sandbox_flavor import (
    DEFAULT_BRIDGE_TIMEOUT_MS,
    CloudflareSandboxConfig,
    CloudflareSandboxSettings,
)
from zenml.logger import get_logger
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
)

if TYPE_CHECKING:
    import httpx


logger = get_logger(__name__)

# Bridge body limit per the documented HTTP API. Beyond this the bridge
# returns 413; we surface a clear error instead.
_BRIDGE_FILE_MAX_BYTES = 32 * 1024 * 1024

# Bridge status codes worth retrying. Cribbed from openai-agents' Cloudflare
# bridge client — 5xx Worker bugs (500) are non-retryable; transient upstream
# / rate-limit codes are.
_RETRYABLE_STATUSES: FrozenSet[int] = frozenset({429, 502, 503, 504})
_MAX_RETRIES = 3


@dataclass(frozen=True)
class _BridgeEvent:
    """One decoded SSE event from the bridge exec stream."""

    kind: Literal["stdout", "stderr", "exit", "error"]
    data: Any


def _sanitize_remote_path(remote_path: str) -> str:
    """Reject paths with `..` segments before they reach the bridge URL.

    Args:
        remote_path: A path inside the sandbox workspace.

    Returns:
        The path stripped of any leading slash, ready for URL composition.

    Raises:
        ValueError: If the normalized path escapes the workspace root.
    """
    stripped = remote_path.lstrip("/")
    if posixpath.normpath(stripped) != stripped or stripped.startswith(".."):
        raise ValueError(
            f"Remote path '{remote_path}' resolves outside the sandbox "
            "workspace."
        )
    return stripped


def _parse_sse_stream(lines: Iterator[str]) -> Iterator[_BridgeEvent]:
    """Parse the bridge's text/event-stream into typed events.

    The inner ``_dispatch`` generator raises ``SandboxExecError`` on
    malformed base64/JSON frames and on ``event: error`` payloads; that
    exception propagates through the ``yield from`` calls below.

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

    Split out from ``exec_stream`` so that function can issue the POST
    eagerly (surfacing 4xx/auth errors at the call site) while only the
    SSE iteration stays deferred to the consumer.

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


class _CloudflareBridgeClient:
    """HTTP wrapper around the bridge's /v1/sandbox/* surface."""

    def __init__(
        self,
        worker_url: str,
        api_key: Optional[str],
        *,
        http_client: Optional["httpx.Client"] = None,
    ) -> None:
        """Initialize the client.

        Args:
            worker_url: Base URL of the deployed bridge Worker.
            api_key: Bearer token for the bridge (``SANDBOX_API_KEY``).
            http_client: Optional pre-built ``httpx.Client``, used for tests.
        """
        import httpx

        self._base = worker_url.rstrip("/")
        headers: Dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if http_client is not None:
            self._client = http_client
            self._owns_client = False
            # Inject auth into the provided client to keep tests honest.
            for k, v in headers.items():
                self._client.headers.setdefault(k, v)
        else:
            self._client = httpx.Client(
                base_url=self._base,
                headers=headers,
                timeout=httpx.Timeout(30.0, read=None),
            )
            self._owns_client = True

    def close(self) -> None:
        """Release the underlying HTTP client."""
        if self._owns_client:
            try:
                self._client.close()
            except Exception:
                logger.debug(
                    "Closing bridge HTTP client failed", exc_info=True
                )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> "httpx.Response":
        """Issue a request with the bridge's retry policy.

        Args:
            method: HTTP verb.
            path: Path under the worker base URL.
            json_body: JSON body for write requests.
            content: Raw bytes body (mutually exclusive with json_body).
            headers: Extra headers.
            stream: When True, return the response without reading it.

        Returns:
            The httpx Response.

        Raises:
            SandboxExecError: On a non-retryable error, or after retries exhausted.
        """
        import httpx

        url = path if path.startswith("http") else self._base + path
        last_exc: Optional[BaseException] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                if stream:
                    req = self._client.build_request(
                        method,
                        url,
                        json=json_body,
                        content=content,
                        headers=headers,
                    )
                    resp = self._client.send(req, stream=True)
                else:
                    resp = self._client.request(
                        method,
                        url,
                        json=json_body,
                        content=content,
                        headers=headers,
                    )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt >= _MAX_RETRIES:
                    raise SandboxExecError(
                        f"Bridge request {method} {path} failed: {e}"
                    ) from e
                time.sleep(0.25 * (2**attempt))
                continue

            if resp.status_code < 400:
                return resp

            retryable = resp.status_code in _RETRYABLE_STATUSES
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

            if not retryable or attempt >= _MAX_RETRIES:
                raise SandboxExecError(
                    f"Bridge {method} {path} returned "
                    f"{resp.status_code}: {body_preview}"
                )
            time.sleep(0.25 * (2**attempt))

        # Defensive: loop above always either returns or raises.
        raise SandboxExecError(
            f"Bridge {method} {path} exhausted retries: {last_exc}"
        )

    def create_sandbox(self) -> str:
        """Create a fresh sandbox.

        Returns:
            The bridge-assigned sandbox id.

        Raises:
            SandboxExecError: If the bridge response is missing an id.
        """
        resp = self._request("POST", "/v1/sandbox", json_body={})
        payload = resp.json()
        sandbox_id = payload.get("id")
        if not sandbox_id:
            raise SandboxExecError(
                f"Bridge create-sandbox response missing 'id': {payload!r}"
            )
        return cast(str, sandbox_id)

    def delete_sandbox(self, sandbox_id: str) -> None:
        """Delete a sandbox.

        Args:
            sandbox_id: The sandbox to delete.
        """
        self._request("DELETE", f"/v1/sandbox/{sandbox_id}")

    def is_running(self, sandbox_id: str) -> bool:
        """Check whether the given sandbox is still alive.

        Args:
            sandbox_id: The sandbox to check.

        Returns:
            True if the bridge reports the sandbox as running.
        """
        resp = self._request("GET", f"/v1/sandbox/{sandbox_id}/running")
        return bool(resp.json().get("running", False))

    def create_bridge_session(
        self, sandbox_id: str, env: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a bridge-side session for scoped env / cwd state.

        Args:
            sandbox_id: The sandbox to scope the session to.
            env: Optional env vars passed in the session body. Verified
                live against the bridge's POST /v1/sandbox/:id/session.

        Returns:
            The bridge session id.

        Raises:
            SandboxExecError: If the bridge response is missing an id.
        """
        body: Optional[Dict[str, Any]] = {"env": env} if env else None
        resp = self._request(
            "POST", f"/v1/sandbox/{sandbox_id}/session", json_body=body
        )
        sid = resp.json().get("id")
        if not sid:
            raise SandboxExecError(
                "Bridge create-session response missing 'id'"
            )
        return cast(str, sid)

    def delete_bridge_session(self, sandbox_id: str, session_id: str) -> None:
        """Delete a bridge-side session.

        Args:
            sandbox_id: The sandbox owning the session.
            session_id: The bridge session id to delete.
        """
        self._request(
            "DELETE", f"/v1/sandbox/{sandbox_id}/session/{session_id}"
        )

    def exec_stream(
        self,
        sandbox_id: str,
        argv: List[str],
        *,
        cwd: Optional[str] = None,
        timeout_ms: int = DEFAULT_BRIDGE_TIMEOUT_MS,
        session_id: Optional[str] = None,
    ) -> Iterator[_BridgeEvent]:
        """Run a command and return an iterator over decoded SSE events.

        The POST is issued eagerly so launch errors (4xx, auth) surface at
        the call site instead of being deferred to the first iteration —
        the returned generator only carries SSE-decoded events.

        Args:
            sandbox_id: The sandbox to exec into.
            argv: Command argv list.
            cwd: Optional working directory.
            timeout_ms: Per-exec timeout in milliseconds.
            session_id: Optional bridge session id to pass via header.

        Returns:
            Iterator of ``_BridgeEvent`` instances in dispatch order.
        """
        body: Dict[str, Any] = {"argv": argv, "timeout_ms": timeout_ms}
        if cwd is not None:
            body["cwd"] = cwd
        headers: Dict[str, str] = {}
        if session_id is not None:
            headers["Session-Id"] = session_id

        resp = self._request(
            "POST",
            f"/v1/sandbox/{sandbox_id}/exec",
            json_body=body,
            headers=headers,
            stream=True,
        )
        return _drain_sse_response(resp)

    def put_file(
        self,
        sandbox_id: str,
        remote_path: str,
        data: bytes,
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Upload raw bytes to a sandbox path.

        Args:
            sandbox_id: The sandbox to write into.
            remote_path: Path inside the sandbox workspace; `..` rejected.
            data: Raw file bytes; max 32 MiB.
            session_id: Optional bridge session id.

        Raises:
            ValueError: If the file exceeds the bridge body limit or the
                remote path is unsafe.
        """
        if len(data) > _BRIDGE_FILE_MAX_BYTES:
            raise ValueError(
                f"File of {len(data)} bytes exceeds the bridge limit of "
                f"{_BRIDGE_FILE_MAX_BYTES} bytes (32 MiB)."
            )
        safe_path = _sanitize_remote_path(remote_path)
        encoded = urllib.parse.quote(safe_path, safe="/")
        headers = {"Content-Type": "application/octet-stream"}
        if session_id is not None:
            headers["Session-Id"] = session_id
        self._request(
            "PUT",
            f"/v1/sandbox/{sandbox_id}/file/{encoded}",
            content=data,
            headers=headers,
        )

    def get_file(
        self,
        sandbox_id: str,
        remote_path: str,
        *,
        session_id: Optional[str] = None,
    ) -> bytes:
        """Download raw bytes from a sandbox path.

        Args:
            sandbox_id: The sandbox to read from.
            remote_path: Path inside the sandbox workspace.
            session_id: Optional bridge session id.

        Returns:
            The raw file contents (bridge caps at 32 MiB).
        """
        safe_path = _sanitize_remote_path(remote_path)
        encoded = urllib.parse.quote(safe_path, safe="/")
        headers: Dict[str, str] = {}
        if session_id is not None:
            headers["Session-Id"] = session_id
        resp = self._request(
            "GET",
            f"/v1/sandbox/{sandbox_id}/file/{encoded}",
            headers=headers,
        )
        return resp.content


class CloudflareSandboxProcess(SandboxProcess):
    """Demuxes a single SSE event iterator into stdout / stderr / exit."""

    def __init__(
        self,
        event_iter: Iterator[_BridgeEvent],
        *,
        session: "CloudflareSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the process wrapper.

        Args:
            event_iter: Iterator yielding bridge SSE events for this exec.
            session: Owning session.
            started_at: Wall-clock launch time.
        """
        super().__init__(session=session, started_at=started_at)
        self._event_iter = event_iter

        # The bridge multiplexes stdout/stderr on one SSE stream. We pump
        # it once on a background thread and demux into two buffers so
        # `stdout()` and `stderr()` can be iterated independently from the
        # caller's thread.
        self._lock = threading.Lock()
        self._stdout_buf: Deque[str] = deque()
        self._stderr_buf: Deque[str] = deque()
        self._data_available = threading.Condition(self._lock)
        self._done = threading.Event()
        self._exit_code: Optional[int] = None
        self._pump_error: Optional[BaseException] = None
        self._stdout_remainder = ""
        self._stderr_remainder = ""

        self._pump = threading.Thread(
            target=self._pump_events, name="cf-bridge-pump", daemon=True
        )
        self._pump.start()

    def _push_text(
        self, target: Deque[str], remainder_attr: str, text: str
    ) -> None:
        """Line-buffer arbitrary text into the target deque.

        Args:
            target: Buffer to append lines to.
            remainder_attr: Name of the per-stream remainder attribute.
            text: New text chunk.
        """
        buf = getattr(self, remainder_attr) + text
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            target.append(line + "\n")
        setattr(self, remainder_attr, buf)

    def _flush_remainders(self) -> None:
        """Push trailing partial lines (no terminating newline) on stream end."""
        if self._stdout_remainder:
            self._stdout_buf.append(self._stdout_remainder)
            self._stdout_remainder = ""
        if self._stderr_remainder:
            self._stderr_buf.append(self._stderr_remainder)
            self._stderr_remainder = ""

    def _pump_events(self) -> None:
        """Background pump: drain SSE iterator into stdout/stderr buffers."""
        try:
            for ev in self._event_iter:
                with self._data_available:
                    if ev.kind == "stdout":
                        self._push_text(
                            self._stdout_buf,
                            "_stdout_remainder",
                            cast(str, ev.data),
                        )
                    elif ev.kind == "stderr":
                        self._push_text(
                            self._stderr_buf,
                            "_stderr_remainder",
                            cast(str, ev.data),
                        )
                    elif ev.kind == "exit":
                        self._exit_code = int(cast(int, ev.data))
                    self._data_available.notify_all()
        except GeneratorExit:
            # kill() closed the iterator. Not an error.
            pass
        except BaseException as e:  # noqa: BLE001
            self._pump_error = e
        finally:
            with self._data_available:
                self._flush_remainders()
                self._done.set()
                self._data_available.notify_all()

    def _iter_buffer(self, buf: Deque[str]) -> Iterator[str]:
        """Block-pop lines from a buffer until the pump signals done.

        Args:
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
            self._iter_buffer(self._stdout_buf), log_level=logging.INFO
        )

    def stderr(self) -> Iterator[str]:
        """Yields stderr lines, routed through the session log source.

        Returns:
            Line iterator wrapped via ``session._wrap_stream`` so each line
            also lands in the per-session ``sandbox:<id>`` log.
        """
        return self._session._wrap_stream(
            self._iter_buffer(self._stderr_buf), log_level=logging.ERROR
        )

    def wait(self, timeout: Optional[float] = None) -> int:
        """Block until the process exits, or ``timeout`` seconds pass.

        Args:
            timeout: Optional wall-clock cap. ``None`` waits indefinitely.

        Returns:
            The exit code captured from the bridge.

        Raises:
            TimeoutError: If ``timeout`` elapsed before the bridge sent an
                ``exit`` frame. The pump keeps running; call ``kill()`` to
                stop it.
            SandboxExecError: If the pump captured an error, or if the SSE
                stream ended without an ``exit`` frame (treated as failure,
                NOT silently as exit code 0 — that would mask real bugs).
        """
        completed = self._done.wait(timeout)
        if not completed:
            raise TimeoutError(
                f"Cloudflare exec did not complete within {timeout}s. "
                "Call process.kill() or session.destroy() to release the "
                "bridge stream."
            )
        pump_err = self._pump_error
        if pump_err is not None:
            if isinstance(pump_err, SandboxExecError):
                raise SandboxExecError(str(pump_err)) from pump_err
            raise SandboxExecError(
                f"Bridge SSE pump failed: {pump_err}"
            ) from pump_err
        if self._exit_code is None:
            # Stream ended cleanly but no exit frame arrived (truncated
            # SSE, killed via kill(), bridge stalled out). Surface this
            # as a failure rather than returning a bogus 0.
            raise SandboxExecError(
                "Cloudflare exec finished without an exit frame; the bridge "
                "stream may have been truncated, killed, or stalled."
            )
        return self._exit_code

    def kill(self) -> None:
        """Stop reading the SSE stream and unblock consumers.

        The bridge has no per-exec kill RPC, so this can't actually
        terminate the in-flight command on Cloudflare's side. What we CAN
        do is close the SSE generator (which closes the underlying httpx
        response and unblocks the pump thread), then signal `_done` so
        `wait()` and `stdout()`/`stderr()` consumers stop waiting.
        Use ``session.destroy()`` to force-terminate the whole sandbox.
        """
        # Closing the generator triggers GeneratorExit inside
        # exec_stream, whose finally clause closes the httpx response.
        try:
            self._event_iter.close()
        except Exception:
            logger.debug(
                "Closing bridge SSE iterator during kill() failed",
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


class CloudflareSandboxSession(SandboxSession):
    """Cloudflare sandbox session over the bridge HTTP API."""

    def __init__(
        self,
        sandbox_id: str,
        *,
        client: _CloudflareBridgeClient,
        parent: "CloudflareSandbox",
        bridge_session_id: Optional[str] = None,
        default_cwd: Optional[str] = None,
        default_timeout_ms: int = DEFAULT_BRIDGE_TIMEOUT_MS,
    ) -> None:
        """Initialize the session.

        Args:
            sandbox_id: The bridge-assigned sandbox id (used as session id).
            client: Bridge HTTP client.
            parent: Owning sandbox component.
            bridge_session_id: Optional bridge-side session id for env scoping.
            default_cwd: Default working directory for execs.
            default_timeout_ms: Default per-exec timeout in milliseconds.
        """
        # Subclass state must be set before super().__init__ so the
        # dashboard hook (invoked during base __init__) has what it needs.
        self._client = client
        self._sandbox_id = sandbox_id
        self._bridge_session_id = bridge_session_id
        self._default_cwd = default_cwd
        self._default_timeout_ms = default_timeout_ms
        self._owns_bridge_session = bridge_session_id is not None
        super().__init__(id=sandbox_id, parent=parent)

    def _get_dashboard_url(self) -> Optional[str]:
        """Bridge sandboxes have no public dashboard URL.

        Returns:
            ``None``.
        """
        return None

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Launch a command in the sandbox.

        Args:
            command: A list (argv) or string (shell-split via ``shlex.split``).
            cwd: Working directory inside the sandbox.
            env: Per-exec env vars. Merged inline into argv as ``KEY=VAL``
                prefixes since the bridge exec endpoint does not document
                an env parameter; session-scoped env created at session
                start is the preferred path.

        Returns:
            A ``CloudflareSandboxProcess``.

        Raises:
            SandboxExecError: If the bridge rejects the launch.
        """
        argv: List[str] = (
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        # Log BEFORE prefixing env=KEY=VAL — per-exec env values are often
        # secrets and would otherwise persist in the sandbox log source.
        self._log_command(argv)
        if env:
            wire_argv = ["env", *[f"{k}={v}" for k, v in env.items()], *argv]
        else:
            wire_argv = argv

        effective_cwd = cwd if cwd is not None else self._default_cwd
        started_at = time.time()
        try:
            event_iter = self._client.exec_stream(
                self._sandbox_id,
                wire_argv,
                cwd=effective_cwd,
                timeout_ms=self._default_timeout_ms,
                session_id=self._bridge_session_id,
            )
        except SandboxExecError:
            raise
        except Exception as e:
            raise SandboxExecError(
                f"Cloudflare bridge exec failed to launch "
                f"({type(e).__name__}): {e}"
            ) from e
        return CloudflareSandboxProcess(
            event_iter, session=self, started_at=started_at
        )

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file into the sandbox.

        Args:
            local_path: Source path on the caller's machine.
            remote_path: Destination path inside the sandbox workspace.
        """
        with open(local_path, "rb") as f:
            data = f.read()
        self._client.put_file(
            self._sandbox_id,
            remote_path,
            data,
            session_id=self._bridge_session_id,
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the sandbox.

        Args:
            remote_path: Source path inside the sandbox workspace.
            local_path: Destination path on the caller's machine.
        """
        data = self._client.get_file(
            self._sandbox_id,
            remote_path,
            session_id=self._bridge_session_id,
        )
        with open(local_path, "wb") as f:
            f.write(data)

    def close(self) -> None:
        """Release bridge-session state, if any. The sandbox keeps running."""
        if self._owns_bridge_session and self._bridge_session_id is not None:
            try:
                self._client.delete_bridge_session(
                    self._sandbox_id, self._bridge_session_id
                )
            except Exception as e:
                logger.debug(
                    "Failed to delete bridge session %s: %s",
                    self._bridge_session_id,
                    e,
                )
            finally:
                self._owns_bridge_session = False
                self._bridge_session_id = None

    def destroy(self) -> None:
        """Terminate the sandbox on Cloudflare."""
        try:
            self._client.delete_sandbox(self._sandbox_id)
        except Exception as e:
            logger.warning(
                "Failed to delete Cloudflare sandbox %s: %s. It may keep "
                "running until the bridge's TTL kicks in.",
                self._sandbox_id,
                e,
                exc_info=True,
            )


class CloudflareSandbox(BaseSandbox):
    """Sandbox flavor backed by a Cloudflare bridge Worker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Cloudflare sandbox component.

        Args:
            *args: Forwarded to ``StackComponent``.
            **kwargs: Forwarded to ``StackComponent``.
        """
        super().__init__(*args, **kwargs)
        self._client: Optional[_CloudflareBridgeClient] = None
        self._client_lock = threading.Lock()

    @property
    def config(self) -> CloudflareSandboxConfig:
        """Typed config.

        Returns:
            The Cloudflare-specific config.
        """
        return cast(CloudflareSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class.

        Returns:
            ``CloudflareSandboxSettings``.
        """
        return CloudflareSandboxSettings

    def _get_client(self) -> _CloudflareBridgeClient:
        """Return the lazily-built bridge HTTP client.

        Returns:
            A cached ``_CloudflareBridgeClient`` bound to this component.
        """
        with self._client_lock:
            if self._client is None:
                self._client = _CloudflareBridgeClient(
                    self.config.worker_url, self.config.api_key
                )
            return self._client

    def cleanup(self) -> None:
        """Close the cached bridge HTTP client.

        Called by ``Stack.cleanup`` when the stack is torn down. Without
        this, the owned httpx.Client (and its connection pool) leaks for
        the lifetime of the process.
        """
        with self._client_lock:
            if self._client is not None:
                try:
                    self._client.close()
                finally:
                    self._client = None
        super().cleanup()

    def _effective_settings(
        self, settings: Optional[BaseSandboxSettings]
    ) -> Tuple[CloudflareSandboxSettings, Dict[str, str]]:
        """Resolve effective settings + env for a session.

        Args:
            settings: Per-call override, if any.

        Returns:
            (effective settings, resolved env dict).
        """
        eff = cast(CloudflareSandboxSettings, self.resolve_settings(settings))
        env = self._resolve_session_environment(eff)
        return eff, env

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Boot a fresh Cloudflare sandbox via the bridge.

        Args:
            settings: Optional per-step overrides.

        Returns:
            A ``CloudflareSandboxSession`` bound to the new sandbox.
        """
        eff, env = self._effective_settings(settings)
        client = self._get_client()
        sandbox_id = client.create_sandbox()

        # Bridge-session env is the only place session-level env is sent.
        # Letting create_bridge_session fail loud means the user sees
        # "missing API key on bridge" instead of "my OPENAI_API_KEY
        # mysteriously isn't visible inside the sandbox".
        bridge_session_id: Optional[str] = None
        if env:
            bridge_session_id = client.create_bridge_session(
                sandbox_id, env=env
            )

        timeout_ms = eff.timeout_ms or DEFAULT_BRIDGE_TIMEOUT_MS
        return CloudflareSandboxSession(
            sandbox_id,
            client=client,
            parent=self,
            bridge_session_id=bridge_session_id,
            default_cwd=eff.cwd,
            default_timeout_ms=timeout_ms,
        )

    def attach(self, session_id: str) -> SandboxSession:
        """Reattach to a still-running Cloudflare sandbox by id.

        Args:
            session_id: The bridge sandbox id to attach to.

        Returns:
            A ``CloudflareSandboxSession`` with no bridge-side session id.

        Raises:
            RuntimeError: If the bridge reports the sandbox as not running.
        """
        client = self._get_client()
        if not client.is_running(session_id):
            raise RuntimeError(
                f"Cloudflare sandbox '{session_id}' is not running."
            )
        eff, _ = self._effective_settings(None)
        timeout_ms = eff.timeout_ms or DEFAULT_BRIDGE_TIMEOUT_MS
        return CloudflareSandboxSession(
            session_id,
            client=client,
            parent=self,
            bridge_session_id=None,
            default_cwd=eff.cwd,
            default_timeout_ms=timeout_ms,
        )
