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
"""Start a ZenML Pro process that gets its identity from the ZenML Pro API.

A warm workspace has no customer yet, so it must not hold an organization or a
workspace name. Its process loads its code, then waits before it reads any
settings. The ZenML Pro API supplies the values when a customer claims the
workspace, and the process finishes starting. The same path runs on every later
restart, which then doesn't wait.
"""

import ast
import importlib
import importlib.util
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import FrameType
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from uuid import UUID

import requests
from pydantic import (
    BaseModel,
    ValidationError,
    model_validator,
)

API_MODULE = "zenml.zen_server.zen_server_api"
ORGANIZATION_ID_ENV = "ZENML_SERVER_PRO_ORGANIZATION_ID"
ORGANIZATION_NAME_ENV = "ZENML_SERVER_PRO_ORGANIZATION_NAME"
WORKSPACE_NAME_ENV = "ZENML_SERVER_PRO_WORKSPACE_NAME"
RESOURCE_POOL_SOURCE_ENV = "ZENML_SERVER_RESOURCE_POOL_IMPLEMENTATION_SOURCE"
ASK_INTERVAL_SECONDS = 1.0
# Only the server decides when a workspace opens, so workers can ask less often.
WORKER_ASK_INTERVAL_SECONDS = 10.0
HTTP_TIMEOUT_SECONDS = 10
READY_REPORT_MAX_INTERVAL_SECONDS = 60.0
MAX_WAITING_THREADS = 32


class WorkspaceIdentity(BaseModel):
    """What the ZenML Pro API says about the workspace of this process."""

    claimed: bool
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    workspace_name: Optional[str] = None
    resource_pool_implementation_source: Optional[str] = None

    @model_validator(mode="after")
    def _claimed_has_organization(self) -> "WorkspaceIdentity":
        """Refuse a claimed workspace that names no organization.

        Returns:
            The validated identity.

        Raises:
            ValueError: If the workspace is claimed but has no organization.
        """
        if self.claimed and self.organization_id is None:
            raise ValueError("A claimed workspace must have an organization.")
        return self


class _ProApi:
    """The calls this process makes before its settings exist."""

    def __init__(self) -> None:
        """Read the connection details, which never depend on the customer."""
        self._url = os.environ["ZENML_SERVER_PRO_API_URL"].rstrip("/")
        self._workspace_id = os.environ["ZENML_SERVER_PRO_WORKSPACE_ID"]
        self._secret = os.environ["ZENML_SERVER_PRO_OAUTH2_CLIENT_SECRET"]
        self._audience = os.environ["ZENML_SERVER_PRO_OAUTH2_AUDIENCE"]
        self._session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    def _authorization(self) -> Dict[str, str]:
        """Log in when needed, so that repeated calls reuse one token.

        Returns:
            The authorization header.
        """
        if self._token is None or time.time() >= self._token_expires_at:
            response = self._session.post(
                f"{self._url}/auth/login",
                data={
                    "client_id": self._workspace_id,
                    "client_secret": self._secret,
                    "audience": self._audience,
                    "grant_type": "client_credentials",
                },
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            token = response.json()
            self._token = token["access_token"]
            self._token_expires_at = time.time() + token["expires_in"] - 60
        return {"Authorization": f"Bearer {self._token}"}

    def _request(self, method: str, path: str) -> requests.Response:
        """Send a request, logging in again if the token was rejected.

        Args:
            method: The HTTP method.
            path: The path under this workspace.

        Returns:
            The successful response.
        """
        url = f"{self._url}/workspaces/{self._workspace_id}/{path}"
        response = self._session.request(
            method,
            url,
            headers=self._authorization(),
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        if response.status_code == 401:
            self._token = None
            response = self._session.request(
                method,
                url,
                headers=self._authorization(),
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
        return response

    def identity(self) -> WorkspaceIdentity:
        """Ask who this workspace belongs to.

        Returns:
            The identity of this workspace.
        """
        return WorkspaceIdentity.model_validate(
            self._request("GET", "identity").json()
        )

    def report_ready(self) -> None:
        """Tell the ZenML Pro API that this server is taking requests."""
        self._request("POST", "ready")


class _WaitingServer(ThreadingHTTPServer):
    """Holds the port until the real server can take it."""

    daemon_threads = True
    answer_ready = False

    def process_request(self, request: Any, client_address: Any) -> None:
        """Drop connections beyond a limit, because anyone can reach this port.

        Args:
            request: The connection.
            client_address: The address of the client.
        """
        if threading.active_count() > MAX_WAITING_THREADS:
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)


class _WaitingHandler(BaseHTTPRequestHandler):
    """Answers health checks and nothing else while the server isn't up."""

    server_version = "ZenML"
    sys_version = ""
    timeout = 5

    def do_GET(self) -> None:
        """Answer a health or readiness check, and refuse anything else."""
        assert isinstance(self.server, _WaitingServer)
        path = self.path.split("?", 1)[0]
        healthy = path == "/health" or (
            path == "/ready" and self.server.answer_ready
        )
        self.send_response(200 if healthy else 503)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Keep health checks out of the logs.

        Args:
            format: The message format.
            *args: The message arguments.
        """


def _exit_on_signal(signum: int, frame: Optional[FrameType]) -> None:
    """Stop waiting when Kubernetes stops the container.

    A process that is PID 1 ignores signals it has no handler for, so without
    this the container would only stop when it gets killed.

    Args:
        signum: The signal number.
        frame: The current stack frame.
    """
    sys.exit(0)


def _ask_until_answered(api: _ProApi) -> WorkspaceIdentity:
    """Ask for the identity until the ZenML Pro API gives a usable answer.

    Args:
        api: The API connection.

    Returns:
        The identity of this workspace.
    """
    while True:
        try:
            return api.identity()
        # A login reply without a usable token raises KeyError or TypeError.
        except (
            requests.RequestException,
            ValidationError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            print(f"Could not get the workspace identity: {e!r}", flush=True)
            time.sleep(ASK_INTERVAL_SECONDS)


def wait_for_identity(
    port: int,
    on_unclaimed: Optional[Callable[[], None]] = None,
    ask_interval_seconds: float = WORKER_ASK_INTERVAL_SECONDS,
) -> None:
    """Put the identity of a claimed workspace into the environment.

    Does nothing if the environment already has an organization, which is how
    every workspace that wasn't created as a warm workspace is configured.

    Args:
        port: The port that health checks arrive on.
        on_unclaimed: Work to do once, if the workspace is still unclaimed.
        ask_interval_seconds: How long to wait between asks while unclaimed.
    """
    if os.environ.get(ORGANIZATION_ID_ENV):
        return

    previous_handler = signal.signal(signal.SIGTERM, _exit_on_signal)
    server = _WaitingServer(("0.0.0.0", port), _WaitingHandler)  # nosec
    threading.Thread(target=server.serve_forever, daemon=True).start()
    api = _ProApi()

    identity = _ask_until_answered(api)
    if not identity.claimed:
        if on_unclaimed:
            on_unclaimed()
        # This lets Helm finish building a warm workspace, so a slot that can't
        # load its code never counts as warm. A claimed workspace that can't
        # reach the API stays out of rotation.
        server.answer_ready = True
        while not identity.claimed:
            time.sleep(ask_interval_seconds)
            identity = _ask_until_answered(api)

    os.environ[ORGANIZATION_ID_ENV] = str(identity.organization_id)
    if identity.organization_name:
        os.environ[ORGANIZATION_NAME_ENV] = identity.organization_name
    if identity.workspace_name:
        os.environ[WORKSPACE_NAME_ENV] = identity.workspace_name
    # An admin's own value wins, as it does on a normal workspace.
    if identity.resource_pool_implementation_source:
        os.environ.setdefault(
            RESOURCE_POOL_SOURCE_ENV,
            identity.resource_pool_implementation_source,
        )

    server.shutdown()
    server.server_close()
    signal.signal(signal.SIGTERM, previous_handler)


@contextmanager
def _reading_settings_fails() -> Iterator[None]:
    """Make any read of the server settings an error.

    Settings read here would be cached for the life of the process, before they
    hold the customer's values.

    Yields:
        Nothing.
    """
    from zenml.config.server_config import (
        ServerConfiguration,
        ServerProConfiguration,
    )

    def refuse(cls: Any) -> Any:
        raise RuntimeError(
            f"{cls.__name__} was read before the workspace identity is known."
        )

    classes: Tuple[Any, ...] = (ServerConfiguration, ServerProConfiguration)
    originals = [
        config_class.__dict__["get_server_config"] for config_class in classes
    ]
    for config_class in classes:
        setattr(config_class, "get_server_config", classmethod(refuse))
    try:
        yield
    finally:
        for config_class, original in zip(classes, originals):
            setattr(config_class, "get_server_config", original)


def _modules_imported_by(module_name: str) -> List[str]:
    """List what a module imports, without importing the module.

    Args:
        module_name: The module to inspect.

    Returns:
        The names of the imported modules.
    """
    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin is not None
    with open(spec.origin, encoding="utf-8") as module_file:
        tree = ast.parse(module_file.read())

    modules: List[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def load_server_code() -> None:
    """Do the slow part of starting a server that needs no settings.

    If any of this reads the server settings, the error stops the warm
    workspace from being built, so no customer ever gets it.
    """
    with _reading_settings_fails():
        for module_name in _modules_imported_by(API_MODULE):
            importlib.import_module(module_name)

        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        service_connector_registry.register_builtin_service_connectors()


def _is_serving(port: int) -> bool:
    """Check whether this server is taking requests.

    Args:
        port: The port of the server.

    Returns:
        Whether the server answered its readiness check.
    """
    try:
        return requests.get(
            f"http://127.0.0.1:{port}/ready", timeout=HTTP_TIMEOUT_SECONDS
        ).ok
    except requests.RequestException:
        return False


def _report_when_serving(port: int) -> None:
    """Tell the ZenML Pro API once this server is taking requests.

    The browser opens the workspace on this report, so it waits for the port.
    Doing it during server startup would be too early. Nothing else can open
    the workspace, so this doesn't give up while the process lives.

    Args:
        port: The port of the server.
    """
    api = _ProApi()
    while not _is_serving(port):
        time.sleep(ASK_INTERVAL_SECONDS)

    retry_interval = ASK_INTERVAL_SECONDS
    while True:
        try:
            api.report_ready()
            return
        except Exception as e:
            print(f"Could not report the server as ready: {e}", flush=True)
        time.sleep(retry_interval)
        retry_interval = min(
            retry_interval * 2, READY_REPORT_MAX_INTERVAL_SECONDS
        )


def main() -> None:
    """Start a server in the same way as `uvicorn` would, once it has an identity."""
    arguments = sys.argv[1:]
    port = int(arguments[arguments.index("--port") + 1])

    wait_for_identity(
        port,
        on_unclaimed=load_server_code,
        ask_interval_seconds=ASK_INTERVAL_SECONDS,
    )

    threading.Thread(
        target=_report_when_serving, args=(port,), daemon=True
    ).start()

    from uvicorn.main import main as uvicorn_main

    sys.argv = ["uvicorn", *arguments]
    uvicorn_main()
