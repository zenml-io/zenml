"""Exercise authentication and bounded adapter extraction with a local server."""

import io
import json
import os
import subprocess
import sys
import tarfile
import threading
from collections.abc import Iterator
from contextlib import nullcontext
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest
from checkpoint_download import download_archive
from training_client import validate_training_url


def archive_bytes(name: str, kind: bytes = tarfile.REGTYPE) -> bytes:
    """Build an archive using the backend's root-directory convention.

    Args:
        name: Archive member path.
        kind: Member type.

    Returns:
        Serialized tar archive.
    """
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        root = tarfile.TarInfo(".")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = "/tmp/escape"
        info.size = 2 if kind == tarfile.REGTYPE else 0
        archive.addfile(info, io.BytesIO(b"{}"))
    return data.getvalue()


@pytest.fixture
def use_pyqwest_transport() -> bool:
    """Select HTTPX unless the SDK transport parity test overrides it.

    Returns:
        Whether the client should use its Pyqwest transport.
    """
    return False


@pytest.fixture
def archive_server(
    use_pyqwest_transport: bool,
) -> Iterator[tuple[str, list[tuple[str, str | None]]]]:
    """Serve test archives only when the exact API key is present.

    Args:
        use_pyqwest_transport: SDK transport selected by the client configuration.

    Yields:
        Local origin and recorded paths and credentials.
    """
    requests: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path != "/api/v1/client/config":
                self.send_error(404)
                return
            if self.headers.get("X-API-Key") != "tml-test-key":
                self.send_error(401)
                return
            payload = json.dumps(
                {"use_pyqwest_transport": use_pyqwest_transport}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            requests.append((self.path, self.headers.get("X-API-Key")))
            if self.headers.get("X-API-Key") != "tml-test-key":
                self.send_error(401)
                return
            if (
                self.path
                == "/api/v1/training_runs/model_test/checkpoints/final/archive"
            ):
                self.send_response(302)
                self.send_header(
                    "Location", f"http://{self.headers['Host']}/archive"
                )
                self.end_headers()
                return
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/archive")
                self.end_headers()
                return
            payload = archive_bytes(
                "../escape" if self.path == "/unsafe" else "./adapter.json",
                tarfile.SYMTYPE
                if self.path == "/symlink"
                else tarfile.REGTYPE,
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_archive_requires_key_and_preserves_files(
    archive_server: tuple[str, list[tuple[str, str | None]]], tmp_path: Path
) -> None:
    """Require authentication and retain only extracted adapter files.

    Args:
        archive_server: Authenticated local server fixture.
        tmp_path: Empty download destination.
    """
    origin, requests = archive_server
    with pytest.raises(HTTPError, match="401"):
        download_archive(origin + "/archive", tmp_path, origin, "wrong")
    download_archive(origin + "/archive", tmp_path, origin, "tml-test-key")
    assert (tmp_path / "adapter.json").read_bytes() == b"{}"
    assert list(tmp_path.iterdir()) == [tmp_path / "adapter.json"]
    assert requests[-1] == ("/archive", "tml-test-key")


@pytest.mark.parametrize("path", ["unsafe", "symlink"])
def test_unsafe_archive_is_rejected(
    archive_server: tuple[str, list[tuple[str, str | None]]],
    tmp_path: Path,
    path: str,
) -> None:
    """Reject traversal and links before writing any files.

    Args:
        archive_server: Authenticated local server fixture.
        tmp_path: Empty download destination.
        path: Endpoint supplying an unsafe archive.
    """
    origin, requests = archive_server
    with pytest.raises(ValueError, match="Unsafe"):
        download_archive(origin + "/" + path, tmp_path, origin, "tml-test-key")
    assert not list(tmp_path.iterdir())
    assert requests == [("/" + path, "tml-test-key")]


def test_redirect_is_not_followed(
    archive_server: tuple[str, list[tuple[str, str | None]]], tmp_path: Path
) -> None:
    """Never forward a credential through an archive redirect.

    Args:
        archive_server: Authenticated local server fixture.
        tmp_path: Empty download destination.
    """
    origin, requests = archive_server
    with pytest.raises(HTTPError, match="302"):
        download_archive(
            origin + "/redirect", tmp_path, origin, "tml-test-key"
        )
    assert requests == [("/redirect", "tml-test-key")]


def test_other_origin_is_rejected_before_request(tmp_path: Path) -> None:
    """Reject another origin before making a network request.

    Args:
        tmp_path: Empty download destination.
    """
    with pytest.raises(ValueError, match="origin"):
        download_archive(
            "http://example.com/weights",
            tmp_path,
            "http://127.0.0.1:80",
            "tml-test-key",
        )


def test_exact_native_origin() -> None:
    """Accept only the exact native service and proxy port."""
    host = "endless-training-0123456789abcdef.test.svc.cluster.local"
    validate_training_url(f"http://{host}:8001", host)
    for url in [
        f"http://{host}:8000",
        "http://example.com:8001",
        f"http://key@{host}:8001",
    ]:
        with pytest.raises(ValueError):
            validate_training_url(url, host)


@pytest.mark.parametrize(
    "use_pyqwest_transport", [False, True], ids=["httpx", "pyqwest"]
)
@pytest.mark.parametrize(
    "checkpoint",
    ["tinker://model_test/final", "tinker://model_test/sampler_weights/final"],
)
def test_checkpoint_cli_uses_real_sdk_and_authenticated_archive_route(
    archive_server: tuple[str, list[tuple[str, str | None]]],
    tmp_path: Path,
    checkpoint: str,
) -> None:
    """Resolve SkyRL checkpoint IDs through the installed SDK and export real files.

    Args:
        archive_server: Local authenticated API and archive endpoints.
        tmp_path: Empty checkpoint destination.
        checkpoint: Short SkyRL or canonical sampler checkpoint reference.
    """
    origin, requests = archive_server
    output = tmp_path / "checkpoint"
    output.mkdir()
    helper = Path(__file__).parents[1] / "checkpoint_download.py"
    result = subprocess.run(
        [sys.executable, str(helper), checkpoint, str(output), origin],
        env={**os.environ, "TINKER_API_KEY": "tml-test-key"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (output / "adapter.json").read_bytes() == b"{}"
    assert list(output.iterdir()) == [output / "adapter.json"]
    assert requests == [
        (
            "/api/v1/training_runs/model_test/checkpoints/final/archive",
            "tml-test-key",
        ),
        ("/archive", "tml-test-key"),
    ]
    assert not (tmp_path / "checkpoint-download-error.json").exists()


def test_malformed_checkpoint_cli_retains_structured_error(
    archive_server: tuple[str, list[tuple[str, str | None]]], tmp_path: Path
) -> None:
    """Persist a parse failure without sending a malformed archive request.

    Args:
        archive_server: Local API fixture recording archive requests.
        tmp_path: Parent directory for the checkpoint and error evidence.
    """
    origin, requests = archive_server
    output = tmp_path / "checkpoint"
    output.mkdir()
    helper = Path(__file__).parents[1] / "checkpoint_download.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "tinker://model_test/../final",
            str(output),
            origin,
        ],
        env={**os.environ, "TINKER_API_KEY": "tml-test-key"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    error = json.loads(
        (tmp_path / "checkpoint-download-error.json").read_text()
    )
    assert error["type"] == "ValueError"
    assert isinstance(error["message"], str) and error["message"]
    assert "tml-test-key" not in json.dumps(error)
    assert requests == []
    assert not list(output.iterdir())


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("read timed out"),
        ConnectionResetError("reset"),
        URLError(TimeoutError("connect timed out")),
        IncompleteRead(b"partial"),
    ],
)
def test_transient_download_restarts_without_partial_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """Discard a partial transport response and publish only a complete archive.

    Args:
        tmp_path: Empty checkpoint destination.
        monkeypatch: Scoped patch helper.
        failure: Transient network failure after partial data.
    """
    partial = Mock()
    partial.read.side_effect = [b"partial broken archive", failure]
    opener = Mock()
    opener.open.side_effect = [
        nullcontext(partial),
        io.BytesIO(archive_bytes("adapter.json")),
    ]
    monkeypatch.setattr(
        "checkpoint_download.build_opener", lambda *args: opener
    )
    download_archive(
        "http://localhost/archive", tmp_path, "http://localhost", "key"
    )
    assert opener.open.call_count == 2
    assert all(
        call.kwargs["timeout"] == 60 for call in opener.open.call_args_list
    )
    assert (tmp_path / "adapter.json").read_bytes() == b"{}"
    assert list(tmp_path.iterdir()) == [tmp_path / "adapter.json"]


def test_transient_download_stops_after_three_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bound repeated transport failures and leave no output files.

    Args:
        tmp_path: Empty checkpoint destination.
        monkeypatch: Scoped patch helper.
    """
    opener = Mock()
    opener.open.side_effect = TimeoutError("read timed out")
    monkeypatch.setattr(
        "checkpoint_download.build_opener", lambda *args: opener
    )
    with pytest.raises(TimeoutError, match="read timed out"):
        download_archive(
            "http://localhost/archive", tmp_path, "http://localhost", "key"
        )
    assert opener.open.call_count == 3
    assert not list(tmp_path.iterdir())


def test_download_deadline_prevents_another_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not restart a failed download after its shared time budget expires.

    Args:
        tmp_path: Empty checkpoint destination.
        monkeypatch: Scoped patch helper.
    """
    opener = Mock()
    opener.open.side_effect = TimeoutError("read timed out")
    monkeypatch.setattr(
        "checkpoint_download.build_opener", lambda *args: opener
    )
    monkeypatch.setattr(
        "checkpoint_download.time.monotonic", Mock(side_effect=[0, 0, 301])
    )
    with pytest.raises(TimeoutError, match="read timed out"):
        download_archive(
            "http://localhost/archive", tmp_path, "http://localhost", "key"
        )
    assert opener.open.call_count == 1
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "payload", [b"not an archive", archive_bytes("../escape")]
)
def test_invalid_archive_is_never_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    """Archive validation errors cannot become transport retries.

    Args:
        tmp_path: Empty checkpoint destination.
        monkeypatch: Scoped patch helper.
        payload: Invalid or unsafe archive content.
    """
    opener = Mock()
    opener.open.return_value = io.BytesIO(payload)
    monkeypatch.setattr(
        "checkpoint_download.build_opener", lambda *args: opener
    )
    with pytest.raises((ValueError, tarfile.TarError)):
        download_archive(
            "http://localhost/archive", tmp_path, "http://localhost", "key"
        )
    assert opener.open.call_count == 1
    assert not list(tmp_path.iterdir())


def test_failed_extraction_leaves_destination_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An error while copying archive contents must not publish partial files.

    Args:
        tmp_path: Empty checkpoint destination.
        monkeypatch: Scoped patch helper.
    """
    opener = Mock()
    opener.open.return_value = io.BytesIO(archive_bytes("adapter.json"))
    monkeypatch.setattr(
        "checkpoint_download.build_opener", lambda *args: opener
    )
    monkeypatch.setattr(
        "checkpoint_download.shutil.copyfileobj",
        Mock(side_effect=OSError("disk full")),
    )
    with pytest.raises(OSError, match="disk full"):
        download_archive(
            "http://localhost/archive", tmp_path, "http://localhost", "key"
        )
    assert opener.open.call_count == 1
    assert not list(tmp_path.iterdir())
