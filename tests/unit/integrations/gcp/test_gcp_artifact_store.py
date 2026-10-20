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
"""Regression tests for GCS I/O deadlines and file finalization."""

import faulthandler
import gc
import json
import logging
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, cast
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
    GCPArtifactStoreConfig,
)

if TYPE_CHECKING:
    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )

PAYLOAD = b"artifact contents"


def _create_store(
    request_timeout: Optional[float] = None,
    read_cache_type: Optional[str] = None,
) -> "GCPArtifactStore":
    """Build an artifact store without accessing a configured ZenML backend.

    Args:
        request_timeout: Optional storage request deadline in seconds.
        read_cache_type: Optional read cache override.

    Returns:
        An artifact store whose filesystem is initialized lazily.
    """
    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )

    now = datetime.now(timezone.utc)
    return GCPArtifactStore(
        id=uuid4(),
        name="gcs-shutdown-test",
        config=GCPArtifactStoreConfig(
            path="gs://bucket",
            request_timeout=request_timeout,
            read_cache_type=read_cache_type,
        ),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=now,
        updated=now,
    )


@contextmanager
def _storage_endpoint(
    stall: bool = False,
) -> Iterator[tuple[str, threading.Event]]:
    """Serve minimal GCS responses or deliberately withhold them.

    Args:
        stall: Whether to withhold responses until the endpoint is stopped.

    Yields:
        The endpoint URL and an event indicating that a request arrived.
    """
    release = threading.Event()
    received = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def do_PUT(self) -> None:
            self._respond()

        def log_message(self, format: str, *args: object) -> None:
            pass

        def _respond(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            received.set()
            if stall:
                release.wait(timeout=20)
                return

            query = parse_qs(urlsplit(self.path).query)
            if query.get("alt") == ["media"]:
                body = PAYLOAD
            else:
                body = json.dumps(
                    {"generation": "1", "size": str(len(PAYLOAD))}
                ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Location",
                f"http://127.0.0.1:"
                f"{cast(ThreadingHTTPServer, self.server).server_port}/upload",
            )
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", received
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_rejects_invalid_request_timeouts(timeout: float) -> None:
    """Configured storage deadlines must be positive and finite.

    Args:
        timeout: An invalid deadline value.
    """
    with pytest.raises(ValidationError):
        GCPArtifactStoreConfig(path="gs://bucket", request_timeout=timeout)


def test_unset_options_preserve_gcsfs_configuration() -> None:
    """Preserve native caching and user-provided fsspec timeout defaults."""
    gcsfs = pytest.importorskip("gcsfs")
    import fsspec.config
    from gcsfs.core import GCSFileSystem

    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )

    with (
        patch.dict(
            fsspec.config.conf,
            {"gcs": {"timeout": 17, "requests_timeout": 23}},
        ),
        patch.object(GCPArtifactStore, "get_credentials", return_value="anon"),
        patch.object(
            gcsfs,
            "GCSFileSystem",
            partial(GCSFileSystem, skip_instance_cache=True),
        ),
        patch.object(
            GCPArtifactStore, "connector_has_expired", return_value=False
        ),
    ):
        store = _create_store()
        assert store.config.request_timeout is None
        assert store.config.read_cache_type is None
        filesystem = store.filesystem
        assert filesystem.timeout == 17
        assert filesystem.requests_timeout == 23
        with (
            patch.object(
                filesystem,
                "info",
                return_value={
                    "name": "bucket/artifact",
                    "size": len(PAYLOAD),
                    "type": "file",
                },
            ),
            filesystem.open("bucket/artifact", "rb") as native_reader,
            store.open("gs://bucket/artifact", "rb") as reader,
        ):
            assert type(reader.cache) is type(native_reader.cache)
            assert reader.timeout == native_reader.timeout


@pytest.mark.parametrize("mode", ["r", "rb", "w", "wb"])
@pytest.mark.parametrize("configured", [False, True])
def test_files_preserve_text_and_binary_io(
    mode: str, configured: bool
) -> None:
    """Real GCS file handles retain read and write behavior with deadlines.

    Args:
        mode: The text or binary read/write mode to exercise.
        configured: Whether to opt into deadlines and read-ahead caching.
    """
    gcsfs = pytest.importorskip("gcsfs")
    from gcsfs.core import GCSFileSystem

    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )

    with (
        _storage_endpoint() as (endpoint, received),
        patch.object(GCPArtifactStore, "get_credentials", return_value="anon"),
        patch.object(
            gcsfs,
            "GCSFileSystem",
            partial(
                GCSFileSystem, endpoint_url=endpoint, skip_instance_cache=True
            ),
        ),
        patch.object(
            GCPArtifactStore, "connector_has_expired", return_value=False
        ),
    ):
        store = _create_store(
            request_timeout=2 if configured else None,
            read_cache_type="readahead" if configured else None,
        )
        filesystem = store.filesystem
        if configured:
            assert filesystem.timeout == 2
            assert filesystem.requests_timeout == 2
        with patch.object(
            filesystem,
            "info",
            return_value={
                "name": "bucket/artifact",
                "size": len(PAYLOAD),
                "type": "file",
            },
        ):
            with store.open("gs://bucket/artifact", mode) as file:
                content = PAYLOAD if "b" in mode else PAYLOAD.decode()
                if "r" in mode:
                    assert file.read() == content
                else:
                    assert file.write(content) == len(content)
        assert received.is_set()


@pytest.mark.parametrize("cleanup", ["close", "gc", "interpreter"])
@pytest.mark.parametrize("mode", ["r", "rb"])
def test_configured_reader_cleanup_after_io_loop_stops(
    cleanup: str, mode: str, tmp_path: Path
) -> None:
    """Closing or finalizing a reader must not wait on a retired I/O loop.

    Args:
        cleanup: Whether to close, collect, or retain the reader until exit.
        mode: The text or binary read mode to exercise.
        tmp_path: Directory for the subprocess's isolated configuration.
    """
    pytest.importorskip("gcsfs")
    _run_probe("reader", cleanup, mode, tmp_path=tmp_path)


def test_configured_log_upload_allows_process_exit(tmp_path: Path) -> None:
    """Final log export can fail without blocking the process indefinitely.

    Args:
        tmp_path: Directory for the subprocess's isolated configuration.
    """
    pytest.importorskip("gcsfs")
    result = _run_probe("logging", tmp_path=tmp_path)
    assert "Failed to export logs to artifact store" in result.stdout


@pytest.mark.parametrize("kind", ["extended-reader", "extended-logging"])
def test_extended_filesystem_shutdown(kind: str, tmp_path: Path) -> None:
    """Newer gcsfs's default filesystem also permits process exit.

    Args:
        kind: The extended filesystem shutdown scenario to exercise.
        tmp_path: Directory for the subprocess's isolated configuration.
    """
    pytest.importorskip("gcsfs.extended_gcsfs")
    _run_probe(kind, "gc", "rb", tmp_path=tmp_path)


def _run_probe(
    kind: str, *args: str, tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    """Check actual interpreter exit after exercising a shutdown failure.

    Args:
        kind: The reader or logging probe to execute.
        *args: Arguments specific to the selected probe.
        tmp_path: Directory for isolated ZenML configuration.

    Returns:
        The completed probe's output and exit status.

    Raises:
        AssertionError: If the probe fails or finalization prevents exit.
    """
    env = os.environ.copy()
    env.update(
        ZENML_ANALYTICS_OPT_IN="false",
        ZENML_DEBUG="true",
        ZENML_CONFIG_PATH=str(tmp_path / "zenml"),
    )
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), kind, *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"{kind} shutdown did not finish:\n"
            f"{error.stdout!r}\n{error.stderr!r}"
        ) from error
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Shutdown probe completed" in result.stdout
    return result


def _probe_reader(cleanup: str, mode: str, extended: bool = False) -> None:
    """Retire the I/O loop before closing or finalizing a real GCS reader.

    Args:
        cleanup: The reader cleanup mechanism to exercise.
        mode: The text or binary read mode to exercise.
        extended: Whether to use the newer default filesystem implementation.
    """
    from gcsfs.core import GCSFileSystem

    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )

    store = _create_store(read_cache_type="readahead")
    if extended:
        from gcsfs.extended_gcsfs import BucketType, ExtendedGcsFileSystem

        filesystem = ExtendedGcsFileSystem(
            token="anon", skip_instance_cache=True
        )
        # A regional bucket selects the same GCSFile read path after the
        # extended filesystem's storage-layout lookup.
        filesystem._storage_layout_cache["bucket"] = (
            BucketType.NON_HIERARCHICAL
        )
    else:
        filesystem = GCSFileSystem(token="anon", skip_instance_cache=True)
    store._filesystem = filesystem
    with (
        patch.object(
            GCPArtifactStore, "connector_has_expired", return_value=False
        ),
        patch.object(
            filesystem,
            "info",
            return_value={
                "name": "bucket/artifact",
                "size": 1024,
                "type": "file",
            },
        ),
    ):
        file = store.open("gs://bucket/artifact", mode)

    loop = filesystem.loop
    stopped = threading.Event()

    def stop_loop() -> None:
        loop.stop()
        stopped.set()

    loop.call_soon_threadsafe(stop_loop)
    assert stopped.wait(timeout=2)
    # Join only the thread for this subprocess's fsspec loop. Leaving the loop
    # object open recreates the finalizer failure in gcsfs 2026.8.1.
    import fsspec.asyn

    fsspec.asyn.iothread[0].join(timeout=2)
    assert not loop.is_running()

    if cleanup == "close":
        file.close()
    elif cleanup == "gc":
        del file
        gc.collect()
    else:
        # Retain the handle until interpreter finalization, after the I/O loop
        # has stopped, instead of relying on local-variable collection timing.
        globals()["retained_reader"] = file


def _probe_logging(extended: bool = False) -> None:
    """Exit after a real GCS log upload receives no HTTP response.

    Args:
        extended: Whether to use the newer default filesystem implementation.
    """
    import gcsfs
    from gcsfs.core import GCSFileSystem

    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )
    from zenml.log_stores.artifact.artifact_log_store import ArtifactLogStore
    from zenml.models import LogsResponse, LogsResponseBody

    filesystem_class = GCSFileSystem
    if extended:
        from gcsfs.extended_gcsfs import BucketType, ExtendedGcsFileSystem

        filesystem_class = ExtendedGcsFileSystem

    with (
        _storage_endpoint(stall=True) as (endpoint, received),
        patch.object(GCPArtifactStore, "get_credentials", return_value="anon"),
        patch.object(
            gcsfs,
            "GCSFileSystem",
            partial(
                filesystem_class,
                endpoint_url=endpoint,
                skip_instance_cache=True,
            ),
        ),
        patch.object(
            GCPArtifactStore, "connector_has_expired", return_value=False
        ),
    ):
        store = _create_store(request_timeout=0.2)
        if extended:
            store.filesystem._storage_layout_cache["bucket"] = (
                BucketType.NON_HIERARCHICAL
            )
        now = datetime.now(timezone.utc)
        model = LogsResponse(
            id=uuid4(),
            body=LogsResponseBody(
                created=now,
                updated=now,
                project_id=uuid4(),
                user_id=uuid4(),
                source="step",
                uri="gs://bucket/logs",
                artifact_store_id=store.id,
            ),
        )
        logs = ArtifactLogStore.from_artifact_store(store)
        with patch.object(store.filesystem, "exists", return_value=True):
            try:
                origin = logs.register_origin("probe", model, {})
                logs.emit(
                    origin,
                    logging.LogRecord(
                        "probe", logging.INFO, "", 0, "finished", (), None
                    ),
                )
                logs.deregister_origin(origin, blocking=True)
            finally:
                logs.deactivate()
        assert received.is_set()


if __name__ == "__main__":
    faulthandler.dump_traceback_later(8)
    if sys.argv[1] in ("reader", "extended-reader"):
        _probe_reader(
            sys.argv[2],
            sys.argv[3],
            extended=sys.argv[1].startswith("extended"),
        )
    else:
        _probe_logging(extended=sys.argv[1].startswith("extended"))
    print("Shutdown probe completed", flush=True)
