#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the ZenML Local deployer."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Generator, Optional, Tuple, Type, cast
from uuid import UUID

from pydantic import BaseModel

from zenml.config.base_settings import BaseSettings
from zenml.deployers.base_deployer import (
    BaseDeployer,
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.deployers.server.app import BaseDeploymentAppRunner
from zenml.enums import DeploymentStatus
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse
from zenml.utils.daemon import (
    get_daemon_pid_if_running,
    run_as_daemon,
    stop_daemon,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.utils.networking_utils import (
    lookup_preferred_or_free_port,
)

logger = get_logger(__name__)


class LocalDeploymentMetadata(BaseModel):
    """Metadata for a local daemon deployment.

    Attributes:
        pid: PID of the daemon process.
        port: TCP port the app listens on.
        address: IP address the app binds to.
        pid_file: Path to PID file.
        log_file: Path to log file.
    """

    pid: Optional[int] = None
    port: Optional[int] = None
    address: Optional[str] = None
    pid_file: Optional[str] = None
    log_file: Optional[str] = None

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "LocalDeploymentMetadata":
        """Build metadata object from a deployment record.

        Args:
            deployment: The deployment to read metadata from.

        Returns:
            Parsed local deployment metadata.
        """
        return cls.model_validate(deployment.deployment_metadata or {})


class LocalDeployerSettings(BaseDeployerSettings):
    """Local deployer settings.

    Attributes:
        port: Preferred port to run on.
        allocate_port_if_busy: Whether to allocate a free port if busy.
        port_range: Range to scan when allocating a free port.
        address: Address to bind the server to.
    """

    port: Optional[int] = None
    allocate_port_if_busy: bool = True
    port_range: Tuple[int, int] = (8000, 65535)
    address: str = "127.0.0.1"


class LocalDeployerConfig(BaseDeployerConfig, LocalDeployerSettings):
    """Local deployer config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component.
        """
        return True


class LocalDeployer(BaseDeployer):
    """Deployer that runs deployments as local daemon processes."""

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Settings class for the local deployer.

        Returns:
            The settings class.
        """
        return LocalDeployerSettings

    @property
    def config(self) -> LocalDeployerConfig:
        """Returns the `LocalDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(LocalDeployerConfig, self._config)

    # ---------- Helpers ----------
    def _runtime_dir(self, deployment_id: UUID) -> str:
        """Compute runtime directory for a deployment.

        Args:
            deployment_id: The deployment UUID.

        Returns:
            Absolute runtime directory path.
        """
        return os.path.join(
            get_global_config_directory(),
            "deployments",
            str(deployment_id),
        )

    def _pid_file_path(self, deployment_id: UUID) -> str:
        """Compute PID file path for a deployment.

        Args:
            deployment_id: The deployment UUID.

        Returns:
            Absolute PID file path.
        """
        return os.path.join(self._runtime_dir(deployment_id), "daemon.pid")

    def _log_file_path(self, deployment_id: UUID) -> str:
        """Compute log file path for a deployment.

        Args:
            deployment_id: The deployment UUID.

        Returns:
            Absolute log file path.
        """
        return os.path.join(self._runtime_dir(deployment_id), "daemon.log")

    def _load_or_default_metadata(
        self, deployment: DeploymentResponse
    ) -> LocalDeploymentMetadata:
        """Load existing metadata or compute defaults.

        Args:
            deployment: The deployment.

        Returns:
            Local deployment metadata with file paths ensured.
        """
        meta = LocalDeploymentMetadata.from_deployment(deployment)
        runtime_dir = self._runtime_dir(deployment.id)
        if not os.path.exists(runtime_dir):
            os.makedirs(runtime_dir, exist_ok=True)

        if not meta.pid_file:
            meta.pid_file = self._pid_file_path(deployment.id)
        if not meta.log_file:
            meta.log_file = self._log_file_path(deployment.id)
        return meta

    # ---------- LCM Operations ----------
    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Provision a local daemon deployment.

        Args:
            deployment: The deployment to run.
            stack: The active stack (unused by local deployer).
            environment: Environment variables for the app.
            secrets: Secret environment variables for the app.
            timeout: Unused for immediate daemonization.

        Returns:
            Operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: If the daemon cannot be started.
        """
        assert deployment.snapshot, "Pipeline snapshot not found"

        child_env: Dict[str, str] = dict(os.environ)
        child_env.update(environment)
        child_env.update(secrets)

        settings = cast(
            LocalDeployerSettings,
            self.get_settings(deployment.snapshot),
        )

        existing_meta = self._load_or_default_metadata(deployment)

        preferred_ports = []  # type: ignore[var-annotated]
        if settings.port:
            preferred_ports.append(settings.port)
        if existing_meta.port:
            preferred_ports.append(existing_meta.port)

        try:
            port = lookup_preferred_or_free_port(
                preferred_ports=preferred_ports,  # type: ignore[arg-type]
                allocate_port_if_busy=settings.allocate_port_if_busy,
                range=settings.port_range,
                address=settings.address,
            )
        except IOError as e:
            raise DeploymentProvisionError(str(e))

        address = settings.address
        pid_file = existing_meta.pid_file or self._pid_file_path(deployment.id)
        log_file = existing_meta.log_file or self._log_file_path(deployment.id)

        runtime_dir = self._runtime_dir(deployment.id)
        if not os.path.exists(runtime_dir):
            os.makedirs(runtime_dir, exist_ok=True)

        def _daemon_entrypoint(
            dep_id: str, host: str, listen_port: int, env: Dict[str, str]
        ) -> None:
            """Entrypoint that runs the deployment app in the daemon.

            Args:
                dep_id: Deployment UUID.
                host: Bind address.
                listen_port: Bind port.
                env: Environment variables to set.
            """
            os.environ.update(env)
            app_runner = BaseDeploymentAppRunner.load_app_runner(dep_id)
            app_runner.settings.uvicorn_host = host
            app_runner.settings.uvicorn_port = listen_port
            app_runner.run()

        try:
            run_as_daemon(
                _daemon_entrypoint,
                pid_file=pid_file,
                log_file=log_file,
                working_directory="/",
            )(
                dep_id=deployment_id,
                host=address,
                listen_port=port,
                env=child_env,
            )
        except FileExistsError as e:
            raise DeploymentProvisionError(str(e))
        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to start daemon for deployment '{deployment.name}': "
                f"{e}"
            ) from e

        pid: Optional[int] = None
        for _ in range(10):
            pid = get_daemon_pid_if_running(pid_file)
            if pid:
                break
            time.sleep(0.1)

        metadata = LocalDeploymentMetadata(
            pid=pid,
            port=port,
            address=address,
            pid_file=pid_file,
            log_file=log_file,
        )

        state = DeploymentOperationalState(
            status=DeploymentStatus.RUNNING
            if pid
            else DeploymentStatus.PENDING,
            metadata=metadata.model_dump(exclude_none=True),
        )
        state.url = f"http://{address}:{port}"
        return state

    def do_get_deployment_state(
        self, deployment: DeploymentResponse
    ) -> DeploymentOperationalState:
        """Get information about a local daemon deployment.

        Args:
            deployment: The deployment to inspect.

        Returns:
            Operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If metadata cannot be resolved.
        """
        meta = self._load_or_default_metadata(deployment)
        if not meta.pid_file:
            raise DeploymentNotFoundError(
                f"Daemon metadata for deployment '{deployment.name}' missing."
            )

        pid = get_daemon_pid_if_running(meta.pid_file)
        state = DeploymentOperationalState(
            status=DeploymentStatus.ABSENT,
            metadata=meta.model_dump(exclude_none=True),
        )

        if pid:
            meta.pid = pid
            addr = meta.address or "127.0.0.1"
            prt = meta.port or 0
            state.metadata = meta.model_dump(exclude_none=True)
            state.status = DeploymentStatus.RUNNING
            if prt:
                state.url = f"http://{addr}:{prt}"

        return state

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Read logs from the local daemon log file.

        Args:
            deployment: The deployment to read logs for.
            follow: Stream logs if True.
            tail: Return only last N lines if set.

        Yields:
            Log lines.

        Raises:
            DeploymentLogsNotFoundError: If the log file is missing.
            DeployerError: For unexpected errors.
        """
        meta = self._load_or_default_metadata(deployment)
        log_file = meta.log_file
        if not log_file or not os.path.exists(log_file):
            raise DeploymentLogsNotFoundError(
                f"Log file not found for deployment '{deployment.name}'"
            )

        try:

            def _read_tail(path: str, n: int) -> Generator[str, bool, None]:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    for line in lines[-n:]:
                        yield line.rstrip("\n")

            if not follow:
                if tail and tail > 0:
                    yield from _read_tail(log_file, tail)
                else:
                    with open(
                        log_file, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        for line in f:
                            yield line.rstrip("\n")
                return

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                if tail and tail > 0:
                    lines = f.readlines()
                    for line in lines[-tail:]:
                        yield line.rstrip("\n")
                else:
                    f.seek(0, os.SEEK_END)

                while True:
                    where = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        f.seek(where)
                        continue
                    yield line.rstrip("\n")

        except DeploymentLogsNotFoundError:
            raise
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while reading logs for deployment "
                f"'{deployment.name}': {e}"
            ) from e

    def do_deprovision_deployment(
        self, deployment: DeploymentResponse, timeout: int
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a local daemon deployment.

        Args:
            deployment: The deployment to stop.
            timeout: Unused for local daemon stop.

        Returns:
            None, indicating immediate deletion completed.

        Raises:
            DeploymentNotFoundError: If the daemon is not found.
            DeploymentDeprovisionError: If stopping fails.
        """
        meta = self._load_or_default_metadata(deployment)
        if not meta.pid_file:
            raise DeploymentNotFoundError(
                f"Daemon metadata for deployment '{deployment.name}' missing."
            )

        pid = get_daemon_pid_if_running(meta.pid_file)
        if not pid:
            raise DeploymentNotFoundError(
                f"Daemon for deployment '{deployment.name}' not found"
            )

        try:
            stop_daemon(meta.pid_file)
        except Exception as e:
            raise DeploymentDeprovisionError(
                f"Failed to stop daemon for deployment '{deployment.name}': "
                f"{e}"
            ) from e

        return None


class LocalDeployerFlavor(BaseDeployerFlavor):
    """Flavor for the Local daemon deployer."""

    @property
    def name(self) -> str:
        """Name of the deployer flavor.

        Returns:
            Flavor name.
        """
        return "local"

    @property
    def config_class(self) -> Type[BaseDeployerConfig]:
        """Config class for the flavor.

        Returns:
            The config class.
        """
        return LocalDeployerConfig

    @property
    def implementation_class(self) -> Type[LocalDeployer]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        return LocalDeployer
