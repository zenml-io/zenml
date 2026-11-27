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
"""Run the current ZenML checkout as an authenticated disposable API server."""

import json
import os
import subprocess
import sys
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator

import requests
from sqlalchemy.engine import make_url
from tests.fuzz.database import DisposableDatabase, api_database

from zenml.utils.networking_utils import find_available_port

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTROL_USERNAME = "zenml-fuzz-control"
CONTROL_PASSWORD = "zenml-fuzz-control-password"
REQUEST_TIMEOUT_SECONDS = 10
START_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class RunningApiServer:
    """Authenticated handle to a running disposable ZenML server."""

    base_url: str
    token: str
    database: DisposableDatabase
    process: subprocess.Popen[bytes]
    output_directory: Path
    log_path: Path

    def tail_log(self, max_lines: int = 40) -> str:
        """Return the last lines of the server log for inline failure reports.

        Args:
            max_lines: Maximum number of trailing lines to return.

        Returns:
            Trailing server log text, or an empty string if unreadable.
        """
        if not self.log_path.exists():
            return ""
        lines = self.log_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        return "\n".join(lines[-max_lines:])


def build_server_command(port: int) -> list[str]:
    """Build the Uvicorn command for the current checkout.

    Args:
        port: Loopback port to bind.

    Returns:
        Command argument list.
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
    """Create a child-only server environment with password auth enabled.

    Args:
        database: Disposable database assigned to the server.
        output_directory: Run-owned directory for server config and stores.

    Returns:
        Environment variable mapping for the child server process.
    """
    database.assert_owned()
    database_url = make_url(database.url)
    store_url = database_url.set(
        drivername=database_url.get_backend_name()
    ).render_as_string(hide_password=False)
    output_directory = output_directory.resolve()
    stripped_prefixes = (
        "ZENML_STORE_",
        "ZENML_SERVER_",
        "ZENML_ACTIVE_",
        "ZENML_SECRETS_STORE_",
        "ZENML_BACKUP_SECRETS_STORE_",
    )
    stripped_exact = {
        "ZENML_CONFIG_PATH",
        "ZENML_LOCAL_STORES_PATH",
        "DISABLE_DATABASE_MIGRATION",
    }
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in stripped_exact and not key.startswith(stripped_prefixes)
    }
    existing_python_path = environment.get("PYTHONPATH")
    python_path = str(REPOSITORY_ROOT)
    if existing_python_path:
        python_path = f"{python_path}{os.pathsep}{existing_python_path}"
    environment.update(
        {
            "AUTO_OPEN_DASHBOARD": "false",
            "PYTHONPATH": python_path,
            "ZENML_ANALYTICS_OPT_IN": "false",
            "ZENML_CONFIG_PATH": str(output_directory / "server-config"),
            "ZENML_DEBUG": "true",
            "ZENML_LOCAL_STORES_PATH": str(output_directory / "local-stores"),
            "ZENML_SERVER": "true",
            "ZENML_SERVER_AUTH_SCHEME": "OAUTH2_PASSWORD_BEARER",
            "ZENML_SERVER_AUTO_ACTIVATE": "false",
            "ZENML_STORE_TYPE": "sql",
            "ZENML_STORE_URL": store_url,
        }
    )
    return environment


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Stop the Uvicorn child process cleanly, escalating to SIGKILL if stuck."""
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    if process.poll() is None:
        raise RuntimeError(
            f"ZenML server process {process.pid} is still running after stop"
        )


def _wait_until_ready(process: subprocess.Popen[bytes], base_url: str) -> None:
    """Poll ``/health`` until ready or fail fast on early exit."""
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    last_error: BaseException | None = None
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
    """Activate the server and return a verified password-bearer token."""
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
            raise RuntimeError("Server login returned no access token")
        verification = requests.get(
            f"{base_url}/api/v1/tags",
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if verification.status_code == 200:
            return token
        # A freshly activated server can reject a same-second token at the
        # password-change boundary. Retry only that transient condition.
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


@contextmanager
def running_api_server(
    backend: str, output_directory: Path
) -> Generator[RunningApiServer, None, None]:
    """Start and tear down an authenticated source-backed ZenML server.

    Uses ``ExitStack`` so process shutdown always runs before database removal
    and both failures are preserved if teardown encounters an error.

    Args:
        backend: Selected database backend (``sqlite`` or ``mysql``).
        output_directory: Run-owned directory for server state and logs.

    Yields:
        Authenticated handle to the running server.
    """
    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    log_path = output_directory / "api-server.log"

    with ExitStack() as stack:
        database = stack.enter_context(api_database(backend, output_directory))
        port = find_available_port()
        base_url = f"http://127.0.0.1:{port}"
        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                build_server_command(port),
                cwd=REPOSITORY_ROOT,
                env=build_server_environment(database, output_directory),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        stack.callback(_stop_process, process)
        _wait_until_ready(process, base_url)
        token = _authenticate(base_url)
        details = {
            "backend": database.backend,
            "base_url": base_url,
            "database_name": database.database_name,
            "pid": process.pid,
            "source_path": str(REPOSITORY_ROOT),
        }
        (output_directory / "api-server.json").write_text(
            json.dumps(details, indent=2, sort_keys=True) + "\n"
        )
        yield RunningApiServer(
            base_url=base_url,
            token=token,
            database=database,
            process=process,
            output_directory=output_directory,
            log_path=log_path,
        )
