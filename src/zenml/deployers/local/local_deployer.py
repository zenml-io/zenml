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

import ipaddress
import os
import shutil
import subprocess
import sys
import time
from typing import (
    TYPE_CHECKING,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

import psutil
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
from zenml.deployers.server.app import (
    start_deployment_app,
)
from zenml.enums import DeploymentStatus
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse
from zenml.utils.daemon import (
    stop_process,
)
from zenml.utils.io_utils import get_global_config_directory
from zenml.utils.networking_utils import (
    lookup_preferred_or_free_port,
)

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

DEFAULT_TAIL_FOLLOW_LINES = 100
DEFAULT_DAEMON_STARTUP_TIMEOUT = 10


class LocalDeploymentMetadata(BaseModel):
    """Metadata for a local daemon deployment.

    Attributes:
        pid: PID of the daemon process.
        port: TCP port the app listens on.
        address: IP address the app binds to.
        log_file: Path to log file.
    """

    pid: Optional[int] = None
    port: Optional[int] = None
    address: Optional[str] = None
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
        blocking: Whether to run the deployment in the current process instead
            of running it as a daemon process.
        auto_reload: Whether to automatically reload the deployment when the
            code changes.
    """

    port: Optional[int] = None
    allocate_port_if_busy: bool = True
    port_range: Tuple[int, int] = (8000, 65535)
    address: str = "127.0.0.1"
    blocking: bool = False
    auto_reload: bool = False


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

        existing_meta = LocalDeploymentMetadata.from_deployment(deployment)

        if existing_meta.pid:
            try:
                stop_process(existing_meta.pid)
            except Exception as e:
                logger.warning(
                    f"Failed to stop existing daemon process for deployment "
                    f"'{deployment.name}' with PID {existing_meta.pid}: {e}"
                )

        preferred_ports: List[int] = []
        if settings.port:
            preferred_ports.append(settings.port)
        if existing_meta.port:
            preferred_ports.append(existing_meta.port)

        try:
            port = lookup_preferred_or_free_port(
                preferred_ports=preferred_ports,
                allocate_port_if_busy=settings.allocate_port_if_busy,
                range=settings.port_range,
                address=settings.address,
            )
        except IOError as e:
            raise DeploymentProvisionError(str(e))

        address = settings.address
        # Validate that the address is a valid IP address
        try:
            ipaddress.ip_address(address)
        except ValueError:
            raise DeploymentProvisionError(
                f"Invalid address: {address}. Must be a valid IP address."
            )

        if address == "0.0.0.0":  # nosec
            address = "localhost"
        url = f"http://{address}:{port}"

        log_file = existing_meta.log_file or self._log_file_path(deployment.id)

        runtime_dir = self._runtime_dir(deployment.id)
        if not os.path.exists(runtime_dir):
            os.makedirs(runtime_dir, exist_ok=True)

        if settings.blocking:
            self._update_deployment(
                deployment,
                DeploymentOperationalState(
                    status=DeploymentStatus.RUNNING,
                    url=url,
                    metadata=LocalDeploymentMetadata(
                        pid=os.getpid(),
                        port=port,
                        address=settings.address,
                    ).model_dump(exclude_none=True),
                ),
            )
            start_deployment_app(
                deployment_id=deployment.id,
                host=settings.address,
                port=port,
                reload=settings.auto_reload,
            )
            self._update_deployment(
                deployment,
                DeploymentOperationalState(
                    status=DeploymentStatus.ABSENT,
                    metadata=None,
                ),
            )
            # Exiting early here because the deployment takes over the current
            # process and anything else is irrelevant.
            sys.exit(0)

        # Launch the deployment app as a background subprocess.
        python_exe = sys.executable
        module = "zenml.deployers.server.app"
        cmd = [
            python_exe,
            "-m",
            module,
            "--deployment_id",
            str(deployment.id),
            "--log_file",
            os.path.abspath(log_file),
            "--host",
            settings.address,
            "--port",
            str(port),
        ]

        if settings.auto_reload:
            cmd.append("--reload")

        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            proc = subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                env=child_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to start subprocess for deployment "
                f"'{deployment.name}': {e}"
            ) from e

        metadata = LocalDeploymentMetadata(
            pid=proc.pid,
            port=port,
            address=settings.address,
            log_file=log_file,
        )

        state = DeploymentOperationalState(
            status=DeploymentStatus.PENDING,
            url=url,
            metadata=metadata.model_dump(exclude_none=True),
        )

        return state

    def do_get_deployment_state(
        self, deployment: DeploymentResponse
    ) -> DeploymentOperationalState:
        """Get information about a local daemon deployment.

        Args:
            deployment: The deployment to inspect.

        Returns:
            Operational state of the deployment.
        """
        assert deployment.snapshot, "Pipeline snapshot not found"
        meta = LocalDeploymentMetadata.from_deployment(deployment)

        state = DeploymentOperationalState(
            status=DeploymentStatus.ERROR,
            metadata=meta.model_dump(exclude_none=True),
        )

        if not meta.pid:
            state.status = DeploymentStatus.ABSENT
            return state

        if not psutil.pid_exists(meta.pid):
            return state

        if not meta.port or not meta.address:
            return state

        # Use pending until we can confirm the daemon is reachable
        state.status = DeploymentStatus.RUNNING
        address = meta.address
        if address == "0.0.0.0":  # nosec
            address = "localhost"
        state.url = f"http://{address}:{meta.port}"

        state.metadata = meta.model_dump(exclude_none=True)

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
        meta = LocalDeploymentMetadata.from_deployment(deployment)
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
                if not tail:
                    tail = DEFAULT_TAIL_FOLLOW_LINES
                lines = f.readlines()
                for line in lines[-tail:]:
                    yield line.rstrip("\n")

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
        meta = LocalDeploymentMetadata.from_deployment(deployment)
        if not meta.pid:
            raise DeploymentNotFoundError(
                f"Daemon for deployment '{deployment.name}' missing."
            )

        try:
            stop_process(meta.pid)
        except Exception as e:
            raise DeploymentDeprovisionError(
                f"Failed to stop daemon for deployment '{deployment.name}': "
                f"{e}"
            ) from e
        else:
            shutil.rmtree(self._runtime_dir(deployment.id))

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
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/deployer/local.png"

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
