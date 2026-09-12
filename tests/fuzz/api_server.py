#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Run the current ZenML source as an authenticated disposable API server."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator, Optional

import requests
from sqlalchemy.engine import make_url
from tests.fuzz.database import DisposableDatabase, api_database

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTROL_USERNAME = "zenml-fuzz-control"
CONTROL_PASSWORD = "zenml-fuzz-control-password"
REQUEST_TIMEOUT_SECONDS = 10
START_TIMEOUT_SECONDS = 60


class ApiServerCleanupError(RuntimeError):
    """Error that retains both a server failure and teardown failure."""

    def __init__(
        self,
        original_error: Optional[BaseException],
        cleanup_error: BaseException,
    ) -> None:
        """Initialize the combined failure.

        Args:
            original_error: Error raised while running the server, if any.
            cleanup_error: Error raised while tearing down the server.
        """
        self.original_error = original_error
        self.cleanup_error = cleanup_error
        super().__init__(
            f"API server cleanup failed: {cleanup_error}; original error: "
            f"{original_error!r}"
        )


@dataclass(frozen=True)
class RunningApiServer:
    """Authenticated handle to a running disposable ZenML server."""

    base_url: str
    token: str
    database: DisposableDatabase
    process: subprocess.Popen[bytes]
    output_directory: Path
    source_path: Path
    source_revision: str


def build_server_command(port: int) -> list[str]:
    """Build the direct Uvicorn command for the current source checkout.

    Args:
        port: Loopback port on which the server should listen.

    Returns:
        Command arguments for launching the server.
    """
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "zenml.zen_server.zen_server_api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
    ]


def build_server_environment(
    database: DisposableDatabase, output_directory: Path
) -> Dict[str, str]:
    """Create a child-only server environment with authentication enabled.

    Args:
        database: Disposable database assigned to the server.
        output_directory: Run-owned directory for server state.

    Returns:
        Environment variables for the server child process.

    """
    database.assert_owned()
    database_url = make_url(database.url)
    store_url = database_url.set(
        drivername=database_url.get_backend_name()
    ).render_as_string(hide_password=False)
    output_directory = output_directory.resolve()
    environment = {
        key: value
        for key, value in os.environ.items()
        if not (
            key == "ZENML_CONFIG_PATH"
            or key == "ZENML_LOCAL_STORES_PATH"
            or key == "DISABLE_DATABASE_MIGRATION"
            or key.startswith("ZENML_STORE_")
            or key.startswith("ZENML_SERVER_")
            or key.startswith("ZENML_ACTIVE_")
        )
    }
    existing_python_path = environment.get("PYTHONPATH")
    python_path = str(REPOSITORY_ROOT)
    if existing_python_path:
        python_path = f"{python_path}{os.pathsep}{existing_python_path}"
    environment.update(
        {
            "PYTHONPATH": python_path,
            "ZENML_CONFIG_PATH": str(output_directory / "server-config"),
            "ZENML_LOCAL_STORES_PATH": str(output_directory / "local-stores"),
            "ZENML_STORE_URL": store_url,
            "ZENML_STORE_TYPE": "sql",
            "ZENML_SERVER": "true",
            "ZENML_SERVER_AUTH_SCHEME": "OAUTH2_PASSWORD_BEARER",
            "ZENML_SERVER_AUTO_ACTIVATE": "false",
            "ZENML_ANALYTICS_OPT_IN": "false",
            "ZENML_DEBUG": "true",
            "AUTO_OPEN_DASHBOARD": "false",
        }
    )
    return environment


def _available_port() -> int:
    """Ask the operating system for an available loopback port.

    Returns:
        An available TCP port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _source_revision() -> str:
    """Return the source revision loaded by the server process.

    Returns:
        The Git revision, or ``unknown`` when it cannot be resolved.
    """
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Stop the server process group and wait for owned children.

    Args:
        process: Server process to stop.
    """
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=5)


def _wait_until_ready(process: subprocess.Popen[bytes], base_url: str) -> None:
    """Wait for the server health endpoint or report early process exit.

    Args:
        process: Server process being monitored.
        base_url: Loopback URL of the server.

    Raises:
        RuntimeError: If the process exits early or readiness times out.
    """
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    last_error: Optional[BaseException] = None
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise RuntimeError(
                f"ZenML server exited before readiness with code {return_code}"
            )
        try:
            response = requests.get(
                f"{base_url}/health", timeout=REQUEST_TIMEOUT_SECONDS
            )
            if response.status_code == 200:
                return
        except requests.RequestException as error:
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(
        f"Timed out waiting for ZenML server readiness: {last_error!r}"
    )


def _authenticate(base_url: str) -> str:
    """Activate the server and obtain a password-bearer token.

    Args:
        base_url: Loopback URL of the disposable server.

    Returns:
        Access token for the control user.

    Raises:
        RuntimeError: If activation, login, or token verification fails.
    """
    activation = requests.put(
        f"{base_url}/api/v1/activate",
        json={
            "admin_username": CONTROL_USERNAME,
            "admin_password": CONTROL_PASSWORD,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if activation.status_code != 200:
        raise RuntimeError(
            f"Server activation failed ({activation.status_code}): "
            f"{activation.text[:500]}"
        )
    for attempt in range(2):
        login = requests.post(
            f"{base_url}/api/v1/login",
            data={
                "grant_type": "password",
                "username": CONTROL_USERNAME,
                "password": CONTROL_PASSWORD,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if login.status_code != 200:
            raise RuntimeError(
                f"Server login failed ({login.status_code}): "
                f"{login.text[:500]}"
            )
        token = login.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError(
                "Server login response did not contain an access token"
            )
        verification = requests.get(
            f"{base_url}/api/v1/tags",
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if verification.status_code == 200:
            return token
        # A freshly activated server can reject a same-second token at the
        # password-change boundary. Retry only that explicit transient error.
        if (
            attempt == 0
            and verification.status_code == 401
            and "issued before the user's password was changed"
            in verification.text
        ):
            time.sleep(1)
            continue
        raise RuntimeError(
            "Server token verification failed "
            f"({verification.status_code}): {verification.text[:500]}"
        )
    raise RuntimeError("Server token verification did not succeed")


def _write_diagnostics(server: RunningApiServer) -> None:
    """Write sanitized server identity needed to reproduce a failure.

    Args:
        server: Running server whose non-secret identity should be recorded.
    """
    details = {
        "backend": server.database.backend,
        "base_url": server.base_url,
        "database_name": server.database.database_name,
        "pid": server.process.pid,
        "source_path": str(server.source_path),
        "source_revision": server.source_revision,
    }
    (server.output_directory / "api-server.json").write_text(
        json.dumps(details, indent=2, sort_keys=True) + "\n"
    )


def _teardown_error(
    process: Optional[subprocess.Popen[bytes]],
    database_context: AbstractContextManager[DisposableDatabase],
) -> Optional[BaseException]:
    """Tear down the server and database while retaining both failures.

    Args:
        process: Server process, if startup reached process creation.
        database_context: Entered disposable database context.

    Returns:
        The teardown failure, or ``None`` when cleanup succeeded.
    """
    cleanup_error: Optional[BaseException] = None
    if process is not None:
        try:
            _stop_process(process)
        except BaseException as error:
            cleanup_error = error
        else:
            if process.poll() is None:
                cleanup_error = RuntimeError(
                    f"ZenML server process {process.pid} is still running "
                    "after teardown"
                )
    try:
        database_context.__exit__(None, None, None)
    except BaseException as error:
        if cleanup_error is None:
            cleanup_error = error
        else:
            cleanup_error = ApiServerCleanupError(cleanup_error, error)
    return cleanup_error


@contextmanager
def running_api_server(
    backend: str, output_directory: Path
) -> Generator[RunningApiServer, None, None]:
    """Start and tear down an authenticated source-backed ZenML server.

    Args:
        backend: Database backend selected for the server.
        output_directory: Run-owned directory for state and diagnostics.

    Yields:
        An authenticated handle to the running server.

    Raises:
        ApiServerCleanupError: If server or database teardown fails.
        BaseException: Re-raises setup or body failures after successful cleanup.
    """
    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    database_context = api_database(backend, output_directory)
    database = database_context.__enter__()
    process: Optional[subprocess.Popen[bytes]] = None
    try:
        port = _available_port()
        base_url = f"http://127.0.0.1:{port}"
        log_path = output_directory / "api-server.log"
        with log_path.open("wb") as log_file:
            process = subprocess.Popen(
                build_server_command(port),
                cwd=REPOSITORY_ROOT,
                env=build_server_environment(database, output_directory),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=os.name == "posix",
            )
        _wait_until_ready(process, base_url)
        token = _authenticate(base_url)
        server = RunningApiServer(
            base_url=base_url,
            token=token,
            database=database,
            process=process,
            output_directory=output_directory,
            source_path=REPOSITORY_ROOT,
            source_revision=_source_revision(),
        )
        _write_diagnostics(server)
        yield server
    except BaseException as original_error:
        cleanup_error = _teardown_error(process, database_context)
        if cleanup_error is not None:
            raise ApiServerCleanupError(
                original_error, cleanup_error
            ) from original_error
        raise
    else:
        cleanup_error = _teardown_error(process, database_context)
        if cleanup_error is not None:
            raise ApiServerCleanupError(None, cleanup_error) from cleanup_error
