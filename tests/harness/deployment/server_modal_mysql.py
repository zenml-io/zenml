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
from typing import Optional

from tests.harness.deployment.base import (
    MYSQL_DEFAULT_PASSWORD,
    MYSQL_DOCKER_IMAGE,
    BaseTestDeployment,
)
from tests.harness.deployment._modal_runtime import (
    ZENML_SERVER_PORT,
    build_server_image,
    check_modal_credentials,
    wait_for_server,
)
from tests.harness.model import (
    DatabaseType,
    DeploymentStoreConfig,
    ServerType,
)

# Sandbox lifetime cap. One CI shard finishes well under an hour; beyond
# that Modal will reap a leaked sandbox on its own, but cap explicitly so
# a test runner crash doesn't leave one running for the full Modal max.
_SANDBOX_TIMEOUT_SECS = 60 * 60
ENV_MODAL_SERVER_URL = "ZENML_MODAL_SERVER_URL"

# Modal app names are <=64 chars; the deployment name + an 8-char random
# suffix leaves plenty of room and keeps names identifiable in the Modal
# dashboard.
_APP_NAME_SUFFIX_LEN = 8


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
    _DB_INTERNAL_URL_FMT = (
        "mysql://root:{password}@127.0.0.1:3306/{database}"
    )

    def __init__(self, config: "object") -> None:  # noqa: D107
        super().__init__(config)  # type: ignore[arg-type]
        self._app: Optional["object"] = None
        self._sandbox: Optional["object"] = None
        self._tunnel_url: Optional[str] = None

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
            return self._sandbox.poll() is None  # type: ignore[attr-defined]
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
                "Using pre-provisioned Modal server for '%s' at %s.",
                self.config.name,
                preprovisioned_server_url,
            )
            return

        if self.is_running:
            logging.info(
                "Deployment '%s' is already running; skipping provisioning.",
                self.config.name,
            )
            return

        check_modal_credentials()
        import modal

        store_url = self._DB_INTERNAL_URL_FMT.format(
            password=self.DB_ROOT_PASSWORD, database=self.DB_NAME
        )
        db_env = {
            "MYSQL_ROOT_PASSWORD": self.DB_ROOT_PASSWORD,
            "MYSQL_DATABASE": self.DB_NAME,
            "ZENML_STORE_URL": store_url,
        }

        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )
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
        self._app = modal.App.lookup(app_name, create_if_missing=True)

        logging.info("Launching Modal sandbox...")
        self._sandbox = modal.Sandbox.create(
            "/usr/local/bin/zenml-modal-entrypoint.sh",
            app=self._app,
            image=image,
            encrypted_ports=[ZENML_SERVER_PORT],
            timeout=_SANDBOX_TIMEOUT_SECS,
        )

        tunnel = self._sandbox.tunnels()[ZENML_SERVER_PORT]
        self._tunnel_url = tunnel.url
        logging.info(
            "Modal sandbox '%s' is up; waiting for server at %s...",
            self._sandbox.object_id,
            self._tunnel_url,
        )

        try:
            wait_for_server(self._tunnel_url)
        except Exception:
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
        if self._sandbox is not None:
            try:
                self._sandbox.terminate()  # type: ignore[attr-defined]
            except Exception as exc:
                # Termination best-effort: if Modal says the sandbox is
                # already gone, we still want to clear our local state so
                # subsequent up() calls succeed.
                logging.warning(
                    "Error terminating Modal sandbox for '%s': %s",
                    self.config.name,
                    exc,
                )
        self._sandbox = None
        self._app = None
        self._tunnel_url = None

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the store config for the running deployment.

        Raises:
            RuntimeError: If the deployment is not running.

        Returns:
            Store config pointing at the Modal tunnel URL.
        """
        from zenml.constants import DEFAULT_PASSWORD, DEFAULT_USERNAME

        preprovisioned_server_url = self._get_preprovisioned_server_url()
        if preprovisioned_server_url:
            return DeploymentStoreConfig(
                url=preprovisioned_server_url,
                username=DEFAULT_USERNAME,
                password=DEFAULT_PASSWORD,
            )

        if not self.is_running or self._tunnel_url is None:
            raise RuntimeError(
                f"The {self.config.name} deployment is not running."
            )
        return DeploymentStoreConfig(
            url=self._tunnel_url,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD,
        )


ServerModalMySQLTestDeployment.register_deployment_class(
    server_type=ServerType.MODAL, database_type=DatabaseType.MYSQL
)
