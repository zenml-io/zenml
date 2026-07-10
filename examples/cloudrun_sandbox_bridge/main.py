"""ZenML sandbox bridge for Google Cloud Run sandboxes.

A minimal synchronous HTTP service that exposes the ZenML sandbox bridge
protocol (v1) on top of the Cloud Run ``sandbox`` CLI. Deploy it to a Cloud
Run service with ``--sandbox-launcher`` enabled; the ZenML ``cloudrun``
sandbox flavor talks to it over HTTPS.

Authentication is delegated to Cloud Run IAM: deploy the service with
``--no-allow-unauthenticated`` and grant callers ``roles/run.invoker``.
Requests that reach this process have already presented a valid Google ID
token.

Endpoints:
    POST   /v1/sandbox                     create a sandbox
    GET    /v1/sandbox/<id>/running        liveness probe
    POST   /v1/sandbox/<id>/exec           run a command, stream SSE
    PUT    /v1/sandbox/<id>/file/<path>    upload a file
    GET    /v1/sandbox/<id>/file/<path>    download a file
    POST   /v1/sandbox/<id>/snapshot       export overlay tarball to GCS
    DELETE /v1/sandbox/<id>                delete a sandbox
"""

import base64
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Set, Tuple

SANDBOX_BIN = os.environ.get("SANDBOX_BIN", "/usr/local/gcp/bin/sandbox")
# /tmp on Cloud Run gen2 is a per-instance in-memory filesystem, not a
# shared multi-user tmp, so a fixed path is safe here.
SHARE_ROOT = os.environ.get("SHARE_ROOT", "/tmp/zenml-share")  # nosec B108
# Mount point of the per-sandbox shared directory inside each sandbox,
# used to move file payloads across the isolation boundary.
SHARE_MOUNT = "/mnt/zenml"
MAX_FILE_BYTES = 32 * 1024 * 1024
DEFAULT_EXEC_TIMEOUT_MS = 120_000

# Sandboxes created by this instance. Persistent sandboxes are
# instance-local, so an id missing here is gone (or belongs to a recycled
# instance) and reads as 404.
_sandboxes: Set[str] = set()
_sandboxes_lock = threading.Lock()

_gcs_client: Optional[Any] = None
_gcs_client_lock = threading.Lock()


def _get_gcs_client() -> Any:
    """Return a lazily-built, shared Cloud Storage client."""
    global _gcs_client
    with _gcs_client_lock:
        if _gcs_client is None:
            from google.cloud import storage

            _gcs_client = storage.Client()
        return _gcs_client


def _parse_gcs_uri(gcs_uri: str) -> Tuple[str, str]:
    """Split a gs:// URI into bucket and blob names."""
    match = re.match(r"^gs://([^/]+)/(.+)$", gcs_uri)
    if not match:
        raise ValueError(f"Invalid gs:// URI: {gcs_uri}")
    bucket_name, blob_name = match.groups()
    return bucket_name, blob_name


def _run_cli(
    args: List[str], timeout: Optional[float] = None
) -> "subprocess.CompletedProcess[bytes]":
    """Run the sandbox CLI and capture output."""
    return subprocess.run(
        [SANDBOX_BIN, *args], capture_output=True, timeout=timeout
    )


def _share_dir(sandbox_id: str) -> str:
    return os.path.join(SHARE_ROOT, sandbox_id)


def _create_sandbox(allow_egress: bool, import_tar: Optional[str]) -> str:
    """Create a detached persistent sandbox with a bind-mounted share dir."""
    sandbox_id = f"sb-{uuid.uuid4().hex[:12]}"
    share = _share_dir(sandbox_id)
    os.makedirs(share, exist_ok=True)

    args = ["run", sandbox_id, "--detach"]
    if allow_egress:
        args.append("--allow-egress")
    if import_tar:
        args += ["--import-tar", import_tar]
    args += [
        "--mount",
        f"type=bind,source={share},destination={SHARE_MOUNT}",
        "--write",
        "--",
        "/bin/sleep",
        "infinity",
    ]
    result = _run_cli(args, timeout=60)
    if result.returncode != 0:
        shutil.rmtree(share, ignore_errors=True)
        raise RuntimeError(
            f"sandbox run failed ({result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:500]}"
        )
    with _sandboxes_lock:
        _sandboxes.add(sandbox_id)
    return sandbox_id


def _delete_sandbox(sandbox_id: str) -> None:
    result = _run_cli(["delete", sandbox_id, "--force"], timeout=60)
    if result.returncode != 0:
        raise RuntimeError(
            f"sandbox delete failed ({result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:500]}"
        )
    with _sandboxes_lock:
        _sandboxes.discard(sandbox_id)
    shutil.rmtree(_share_dir(sandbox_id), ignore_errors=True)


def _is_running(sandbox_id: str) -> bool:
    with _sandboxes_lock:
        if sandbox_id not in _sandboxes:
            return False
    result = _run_cli(["exec", sandbox_id, "--", "/bin/true"], timeout=30)
    return result.returncode == 0


def _exec_in_sandbox(
    sandbox_id: str,
    argv: List[str],
    cwd: Optional[str],
    env: Dict[str, str],
) -> "subprocess.Popen[bytes]":
    """Launch a command in the sandbox, pipes attached."""
    args = ["exec", sandbox_id]
    for key, value in env.items():
        args += ["-e", f"{key}={value}"]
    if cwd:
        args += ["-w", cwd]
    args += ["--", *argv]
    return subprocess.Popen(
        [SANDBOX_BIN, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _sandbox_shell(sandbox_id: str, script: str) -> None:
    """Run a short shell script inside the sandbox, raising on failure."""
    result = _run_cli(
        ["exec", sandbox_id, "--", "/bin/sh", "-c", script], timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"sandbox exec failed ({result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:500]}"
        )


def _snapshot_to_gcs(sandbox_id: str, gcs_uri: str) -> None:
    """Export the sandbox overlay with `sandbox tar` and upload it to GCS."""
    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)

    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tar_path = tmp.name
    try:
        result = _run_cli(["tar", sandbox_id, "--file", tar_path], timeout=600)
        if result.returncode != 0:
            raise RuntimeError(
                f"sandbox tar failed ({result.returncode}): "
                f"{result.stderr.decode(errors='replace')[:500]}"
            )
        client = _get_gcs_client()
        client.bucket(bucket_name).blob(blob_name).upload_from_filename(
            tar_path
        )
    finally:
        os.unlink(tar_path)


def _download_import_tar(gcs_uri: str) -> str:
    """Fetch a snapshot tarball from GCS to a local temp path."""
    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)

    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tar_path = tmp.name
    client = _get_gcs_client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(tar_path)
    return tar_path


def _safe_sandbox_path(path: str) -> str:
    """Normalize a sandbox-relative path, rejecting traversal."""
    stripped = urllib.parse.unquote(path).lstrip("/")
    normalized = posixpath.normpath(stripped)
    if normalized != stripped or normalized.split("/", 1)[0] == "..":
        raise ValueError(f"Unsafe path: {path}")
    return "/" + normalized


class BridgeHandler(BaseHTTPRequestHandler):
    """Request handler implementing the bridge protocol."""

    protocol_version = "HTTP/1.1"

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_FILE_BYTES:
            raise ValueError("Request body exceeds 32 MiB limit")
        return self.rfile.read(length)

    def _read_json(self) -> Dict[str, Any]:
        body = self._read_body()
        return json.loads(body) if body else {}

    def _route(self) -> Optional[Tuple[str, str, str]]:
        """Split the path into (sandbox_id, action, rest)."""
        parts = self.path.split("?", 1)[0].split("/")
        # /v1/sandbox[/<id>[/<action>[/rest...]]]
        if len(parts) < 3 or parts[1] != "v1" or parts[2] != "sandbox":
            return None
        sandbox_id = parts[3] if len(parts) > 3 else ""
        action = parts[4] if len(parts) > 4 else ""
        rest = "/".join(parts[5:])
        return sandbox_id, action, rest

    def _known_sandbox(self, sandbox_id: str) -> bool:
        # Membership fully decides: the registry only ever contains ids
        # this process minted itself.
        with _sandboxes_lock:
            return sandbox_id in _sandboxes

    def do_POST(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            self._send_error_json(404, "Not found")
            return
        sandbox_id, action, _ = route
        try:
            if not sandbox_id:
                self._handle_create()
            elif not self._known_sandbox(sandbox_id):
                self._send_error_json(404, "Unknown sandbox")
            elif action == "exec":
                self._handle_exec(sandbox_id)
            elif action == "snapshot":
                self._handle_snapshot(sandbox_id)
            else:
                self._send_error_json(404, "Not found")
        except Exception as e:
            self._send_error_json(500, str(e))

    def do_GET(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            self._send_error_json(404, "Not found")
            return
        sandbox_id, action, rest = route
        try:
            if not self._known_sandbox(sandbox_id):
                self._send_error_json(404, "Unknown sandbox")
            elif action == "running":
                self._send_json(200, {"running": _is_running(sandbox_id)})
            elif action == "file" and rest:
                self._handle_get_file(sandbox_id, rest)
            else:
                self._send_error_json(404, "Not found")
        except Exception as e:
            self._send_error_json(500, str(e))

    def do_PUT(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            self._send_error_json(404, "Not found")
            return
        sandbox_id, action, rest = route
        try:
            if not self._known_sandbox(sandbox_id):
                self._send_error_json(404, "Unknown sandbox")
            elif action == "file" and rest:
                self._handle_put_file(sandbox_id, rest)
            else:
                self._send_error_json(404, "Not found")
        except ValueError as e:
            self._send_error_json(413, str(e))
        except Exception as e:
            self._send_error_json(500, str(e))

    def do_DELETE(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            self._send_error_json(404, "Not found")
            return
        sandbox_id, action, _ = route
        try:
            if not sandbox_id or action:
                self._send_error_json(404, "Not found")
            elif not self._known_sandbox(sandbox_id):
                self._send_error_json(404, "Unknown sandbox")
            else:
                _delete_sandbox(sandbox_id)
                self._send_json(200, {"deleted": sandbox_id})
        except Exception as e:
            self._send_error_json(500, str(e))

    def _handle_create(self) -> None:
        payload = self._read_json()
        import_tar_uri = payload.get("import_tar_uri")
        import_tar = (
            _download_import_tar(import_tar_uri) if import_tar_uri else None
        )
        try:
            sandbox_id = _create_sandbox(
                allow_egress=bool(payload.get("allow_egress")),
                import_tar=import_tar,
            )
        finally:
            if import_tar:
                os.unlink(import_tar)
        self._send_json(200, {"id": sandbox_id})

    def _handle_exec(self, sandbox_id: str) -> None:
        payload = self._read_json()
        argv = payload.get("argv")
        if not isinstance(argv, list) or not argv:
            self._send_error_json(400, "Missing argv")
            return
        timeout_ms = int(payload.get("timeout_ms", DEFAULT_EXEC_TIMEOUT_MS))
        proc = _exec_in_sandbox(
            sandbox_id,
            [str(a) for a in argv],
            payload.get("cwd"),
            dict(payload.get("env") or {}),
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        write_lock = threading.Lock()

        def _emit(kind: str, data: str) -> None:
            frame = f"event: {kind}\ndata: {data}\n\n".encode()
            with write_lock:
                chunk = f"{len(frame):x}\r\n".encode() + frame + b"\r\n"
                self.wfile.write(chunk)
                self.wfile.flush()

        def _pump(stream: Any, kind: str) -> None:
            while True:
                chunk = stream.read(16384)
                if not chunk:
                    return
                _emit(kind, base64.b64encode(chunk).decode("ascii"))

        threads = [
            threading.Thread(
                target=_pump, args=(proc.stdout, "stdout"), daemon=True
            ),
            threading.Thread(
                target=_pump, args=(proc.stderr, "stderr"), daemon=True
            ),
        ]
        for t in threads:
            t.start()

        timed_out = False
        try:
            proc.wait(timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
        for t in threads:
            t.join()

        try:
            if timed_out:
                _emit(
                    "error",
                    json.dumps(
                        {"error": f"exec timed out after {timeout_ms}ms"}
                    ),
                )
            else:
                _emit("exit", json.dumps({"exit_code": proc.returncode}))
            with write_lock:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
        except BrokenPipeError:
            # Client hung up (kill()); the sandbox command was already
            # reaped above, so there is nothing to clean up.
            pass

    def _handle_put_file(self, sandbox_id: str, rest: str) -> None:
        dest = _safe_sandbox_path(rest)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_FILE_BYTES:
            raise ValueError("Request body exceeds 32 MiB limit")
        staging_name = f"put-{uuid.uuid4().hex}"
        staging_host = os.path.join(_share_dir(sandbox_id), staging_name)
        # Stream straight to the staging file so concurrent uploads don't
        # each hold a full 32 MiB body in memory.
        with open(staging_host, "wb") as f:
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 1024 * 1024))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        try:
            _sandbox_shell(
                sandbox_id,
                f"mkdir -p {shlex.quote(posixpath.dirname(dest) or '/')} && "
                f"cp {shlex.quote(f'{SHARE_MOUNT}/{staging_name}')} "
                f"{shlex.quote(dest)}",
            )
        finally:
            os.unlink(staging_host)
        self._send_json(200, {"written": dest})

    def _handle_get_file(self, sandbox_id: str, rest: str) -> None:
        src = _safe_sandbox_path(rest)
        staging_name = f"get-{uuid.uuid4().hex}"
        staging_host = os.path.join(_share_dir(sandbox_id), staging_name)
        # Enforce the size limit inside the sandbox BEFORE copying, so a
        # multi-GB file is rejected without paying the copy.
        quoted_src = shlex.quote(src)
        _sandbox_shell(
            sandbox_id,
            f"size=$(wc -c < {quoted_src}) && "
            f'[ "$size" -le {MAX_FILE_BYTES} ] || '
            f"{{ echo 'file exceeds 32 MiB limit' >&2; exit 92; }} && "
            f"cp {quoted_src} "
            f"{shlex.quote(f'{SHARE_MOUNT}/{staging_name}')}",
        )
        try:
            size = os.path.getsize(staging_host)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            with open(staging_host, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        finally:
            os.unlink(staging_host)

    def _handle_snapshot(self, sandbox_id: str) -> None:
        payload = self._read_json()
        gcs_uri = payload.get("gcs_uri")
        if not gcs_uri:
            self._send_error_json(400, "Missing gcs_uri")
            return
        _snapshot_to_gcs(sandbox_id, gcs_uri)
        self._send_json(200, {})

    def log_message(self, format: str, *args: Any) -> None:
        # Route access logs to stdout for Cloud Logging.
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    os.makedirs(SHARE_ROOT, exist_ok=True)
    # Cloud Run containers must listen on all interfaces; IAM/ingress
    # controls sit in front of the service.
    server = ThreadingHTTPServer(("0.0.0.0", port), BridgeHandler)  # nosec B104
    print(f"ZenML sandbox bridge listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
