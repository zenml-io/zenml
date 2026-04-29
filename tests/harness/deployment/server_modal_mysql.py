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
"""Modal-hosted ZenML server + MySQL test deployment."""

import logging
import os
import sys
import uuid
from typing import Mapping, Optional, Protocol

from tests.harness.deployment._modal_runtime import (
    ZENML_SERVER_PORT,
    build_server_image,
    check_modal_credentials,
    stop_modal_app,
    wait_for_server,
)
from tests.harness.deployment.base import (
    MYSQL_DEFAULT_PASSWORD,
    MYSQL_DOCKER_IMAGE,
    BaseTestDeployment,
)
from tests.harness.model import (
    DatabaseType,
    DeploymentStoreConfig,
    ServerType,
)
from zenml.constants import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    ENV_ZENML_DEFAULT_USER_NAME,
    ENV_ZENML_DEFAULT_USER_PASSWORD,
)

# Sandbox lifetime cap. One CI shard finishes well under an hour; beyond
# that Modal will reap a leaked sandbox on its own, but cap explicitly so
# a test runner crash doesn't leave one running for the full Modal max.
_SANDBOX_TIMEOUT_SECS = 60 * 60
ENV_MODAL_SERVER_URL = "ZENML_MODAL_SERVER_URL"
ENV_MODAL_SERVER_USERNAME = "ZENML_MODAL_SERVER_USERNAME"
ENV_MODAL_SERVER_PASSWORD = "ZENML_MODAL_SERVER_PASSWORD"

# Modal app names are <=64 chars; the deployment name + an 8-char random
# suffix leaves plenty of room and keeps names identifiable in the Modal
# dashboard.
_APP_NAME_SUFFIX_LEN = 8


class _ModalTunnel(Protocol):
    """Modal tunnel attributes used by this deployment."""

    url: str


class _ModalSandbox(Protocol):
    """Modal sandbox methods used by this deployment."""

    object_id: object

    def poll(self) -> Optional[object]:
        """Returns a value once the sandbox has stopped."""
        ...

    def tunnels(self) -> Mapping[int, _ModalTunnel]:
        """Returns the sandbox port tunnels."""
        ...

    def terminate(self) -> None:
        """Terminates the sandbox."""
        ...


class ServerModalMySQLTestDeployment(BaseTestDeployment):
    """ZenML server + MySQL running together inside a single Modal sandbox.

    The sandbox is built per CI run from the current repo source (so code
    changes land in the image) and is torn down when the test session
    ends. MySQL is started in the background via the upstream
    ``docker-entrypoint.sh`` and the ZenML server runs in the foreground,
    reachable from the test runner through a Modal TLS tunnel.
    """

    DB_IMAGE = MYSQL_DOCKER_IMAGE
    DB_ROOT_PASSWORD = MYSQL_DEFAULT_PASSWORD
    DB_NAME = "zenml"
    # MySQL listens on its default port on localhost inside the sandbox;
    # the ZenML server connects over 127.0.0.1 so we never expose it
    # outside the sandbox.
    _DB_INTERNAL_URL_FMT = "mysql://root:{password}@127.0.0.1:3306/{database}"

    def __init__(self, config: "object") -> None:  # noqa: D107
        super().__init__(config)  # type: ignore[arg-type]
        self._app: Optional["object"] = None
        self._app_name: Optional[str] = None
        self._sandbox: Optional[_ModalSandbox] = None
        self._tunnel_url: Optional[str] = None
        self._server_credentials: Optional[tuple[str, str]] = None

    @property
    def app_name(self) -> Optional[str]:
        """Returns the Modal app name for a locally managed deployment."""
        return self._app_name

    @property
    def sandbox_id(self) -> Optional[str]:
        """Returns the Modal sandbox ID for a locally managed deployment."""
        if self._sandbox is None:
            return None
        return str(self._sandbox.object_id)

    def _get_preprovisioned_server_url(self) -> Optional[str]:
        """Returns the externally managed server URL, if one was injected."""
        server_url = os.getenv(ENV_MODAL_SERVER_URL)
        return server_url or None

    def _get_server_credentials(self) -> tuple[str, str]:
        """Returns Modal REST credentials, with local defaults as fallback."""
        return (
            os.getenv(ENV_MODAL_SERVER_USERNAME) or DEFAULT_USERNAME,
            os.getenv(ENV_MODAL_SERVER_PASSWORD) or DEFAULT_PASSWORD,
        )

    @property
    def is_running(self) -> bool:
        """Returns whether the sandbox is still alive.

        Returns:
            True while the Modal sandbox is up and a tunnel URL is known.
        """
        if self._get_preprovisioned_server_url():
            return True
        if self._sandbox is None or self._tunnel_url is None:
            return False
        try:
            return self._sandbox.poll() is None
        except Exception:
            # If the Modal SDK raises because the sandbox was reaped out
            # from under us, treat it as "not running" so `up()` can
            # cleanly bring a fresh one back.
            return False

    def up(self) -> None:
        """Builds the Modal image, launches a sandbox, waits for ready.

        Raises:
            RuntimeError: If Modal credentials are missing or the server
                does not become healthy within the configured timeout.
        """
        preprovisioned_server_url = self._get_preprovisioned_server_url()
        if preprovisioned_server_url:
            logging.info(
                "Using pre-provisioned Modal server for '%s'.",
                self.config.name,
            )
            return

        if self.is_running:
            logging.info(
                "Deployment '%s' is already running; skipping provisioning.",
                self.config.name,
            )
            return

        check_modal_credentials()
        import modal  # type: ignore[import-not-found]

        store_url = self._DB_INTERNAL_URL_FMT.format(
            password=self.DB_ROOT_PASSWORD, database=self.DB_NAME
        )
        db_env = {
            "MYSQL_ROOT_PASSWORD": self.DB_ROOT_PASSWORD,
            "MYSQL_DATABASE": self.DB_NAME,
            "ZENML_STORE_URL": store_url,
        }

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        logging.info(
            "Building Modal image for '%s' (db=%s, python=%s)...",
            self.config.name,
            self.DB_IMAGE,
            python_version,
        )
        image = build_server_image(
            db_image=self.DB_IMAGE,
            python_version=python_version,
            db_env=db_env,
        )

        app_name = (
            f"zenml-test-{self.config.name}-"
            f"{uuid.uuid4().hex[:_APP_NAME_SUFFIX_LEN]}"
        )[:64]
        logging.info("Creating Modal app '%s'...", app_name)
        self._app_name = app_name
        self._app = modal.App.lookup(app_name, create_if_missing=True)

        username, password = self._get_server_credentials()
        self._server_credentials = (username, password)
        server_credentials_secret = modal.Secret.from_dict(
            {
                ENV_ZENML_DEFAULT_USER_NAME: username,
                ENV_ZENML_DEFAULT_USER_PASSWORD: password,
            }
        )

        logging.info("Launching Modal sandbox...")
        self._sandbox = modal.Sandbox.create(
            "/usr/local/bin/zenml-modal-entrypoint.sh",
            app=self._app,
            image=image,
            encrypted_ports=[ZENML_SERVER_PORT],
            secrets=[server_credentials_secret],
            timeout=_SANDBOX_TIMEOUT_SECS,
        )

        tunnel = self._sandbox.tunnels()[ZENML_SERVER_PORT]
        self._tunnel_url = tunnel.url
        logging.info(
            "Modal sandbox '%s' is up; waiting for server health check...",
            self._sandbox.object_id,
        )

        try:
            wait_for_server(self._tunnel_url)
        except RuntimeError:
            # A healthy sandbox that never serves is worse than useless;
            # tear it down so the caller doesn't pay for it.
            self._terminate_sandbox()
            raise

        logging.info("Deployment '%s' is ready.", self.config.name)

    def down(self) -> None:
        """Tears down the Modal sandbox (if any)."""
        if self._sandbox is None and self._get_preprovisioned_server_url():
            logging.info(
                "Deployment '%s' is externally managed; skipping teardown.",
                self.config.name,
            )
            return
        self._terminate_sandbox()

    def _terminate_sandbox(self) -> None:
        """Terminates the sandbox and clears local references."""
        app_name = self._app_name
        if self._sandbox is not None:
            try:
                self._sandbox.terminate()
            except Exception as exc:
                # Termination best-effort: if Modal says the sandbox is
                # already gone, we still want to clear our local state so
                # subsequent up() calls succeed.
                logging.warning(
                    "Error terminating Modal sandbox for '%s': %s",
                    self.config.name,
                    exc,
                )
        if app_name:
            stop_modal_app(app_name)
        self._sandbox = None
        self._app = None
        self._app_name = None
        self._tunnel_url = None
        self._server_credentials = None

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the running deployment.

        Raises:
            RuntimeError: If the deployment is not running.

        Returns:
            Store config pointing at the Modal tunnel URL.
        """
        preprovisioned_server_url = self._get_preprovisioned_server_url()
        if preprovisioned_server_url:
            username, password = self._get_server_credentials()
            return DeploymentStoreConfig(
                url=preprovisioned_server_url,
                username=username,
                password=password,
            )

        if not self.is_running or self._tunnel_url is None:
            raise RuntimeError(
                f"The {self.config.name} deployment is not running."
            )
        username, password = (
            self._server_credentials or self._get_server_credentials()
        )
        return DeploymentStoreConfig(
            url=self._tunnel_url,
            username=username,
            password=password,
        )


ServerModalMySQLTestDeployment.register_deployment_class(
    server_type=ServerType.MODAL, database_type=DatabaseType.MYSQL
)
