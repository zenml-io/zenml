#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import os
import subprocess
import sys
import time
from typing import ClassVar, Optional, Tuple, Union, cast

from kubernetes import config as k8s_config
from ml_metadata.proto import metadata_store_pb2

from zenml.exceptions import ProvisioningError
from zenml.integrations.constants import KUBEFLOW
from zenml.integrations.kubeflow import KUBEFLOW_METADATA_STORE_FLAVOR
from zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator import (
    KubeflowOrchestrator,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata_stores import BaseMetadataStore
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.stack.stack import Stack
from zenml.utils import networking_utils

logger = get_logger(__name__)


def inside_kfp_pod() -> bool:
    """Returns if the current python process is running inside a KFP Pod."""
    if "KFP_POD_NAME" not in os.environ:
        return False

    try:
        k8s_config.load_incluster_config()
        return True
    except k8s_config.ConfigException:
        return False


DEFAULT_KFP_METADATA_GRPC_PORT = 8081
DEFAULT_KFP_METADATA_DAEMON_TIMEOUT = 60


class KubeflowMetadataStore(BaseMetadataStore):
    """Kubeflow GRPC backend for ZenML metadata store."""

    upgrade_migration_enabled: bool = False
    host: str = "127.0.0.1"
    port: int = DEFAULT_KFP_METADATA_GRPC_PORT

    # Class Configuration
    FLAVOR: ClassVar[str] = KUBEFLOW_METADATA_STORE_FLAVOR

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a KFP orchestrator."""

        def _ensure_kfp_orchestrator(stack: Stack) -> Tuple[bool, str]:
            return (
                stack.orchestrator.FLAVOR == KUBEFLOW,
                "The Kubeflow metadata store can only be used with a Kubeflow "
                "orchestrator.",
            )

        return StackValidator(
            custom_validation_function=_ensure_kfp_orchestrator
        )

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for the kubeflow metadata store."""
        connection_config = metadata_store_pb2.MetadataStoreClientConfig()
        if inside_kfp_pod():
            connection_config.host = os.environ["METADATA_GRPC_SERVICE_HOST"]
            connection_config.port = int(
                os.environ["METADATA_GRPC_SERVICE_PORT"]
            )
        else:
            if not self.is_running:
                raise RuntimeError(
                    "The KFP metadata daemon is not running. Please run the "
                    "following command to start it first:\n\n"
                    "    'zenml metadata-store up'\n"
                )
            connection_config.host = self.host
            connection_config.port = self.port
        return connection_config

    @property
    def kfp_orchestrator(self) -> KubeflowOrchestrator:
        """Returns the Kubeflow orchestrator in the active stack."""
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        return cast(KubeflowOrchestrator, repo.active_stack.orchestrator)

    @property
    def kubernetes_context(self) -> str:
        """Returns the kubernetes context to the cluster where the Kubeflow
        Pipelines services are running."""
        kubernetes_context = self.kfp_orchestrator.kubernetes_context

        # will never happen, but mypy doesn't know that
        assert kubernetes_context is not None
        return kubernetes_context

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning
        this KFP metadata store.

        Note: the root directory for the KFP metadata store is relative to the
        root directory of the KFP orchestrator, because it is a sub-component
        of it.
        """
        return os.path.join(
            self.kfp_orchestrator.root_directory,
            "metadata-store",
            str(self.uuid),
        )

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file."""
        return os.path.join(self.root_directory, "kubeflow_daemon.pid")

    @property
    def _log_file(self) -> str:
        """Path of the daemon log file."""
        return os.path.join(self.root_directory, "kubeflow_daemon.log")

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run locally."""
        return fileio.exists(self.root_directory)

    @property
    def is_running(self) -> bool:
        """If the component is running locally."""
        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            if not check_if_daemon_is_running(self._pid_file_path):
                return False
        else:
            # Daemon functionality is not supported on Windows, so the PID
            # file won't exist. This if clause exists just for mypy to not
            # complain about missing functions
            pass

        return True

    def provision(self) -> None:
        """Provisions resources to run the component locally."""
        logger.info("Provisioning local Kubeflow Pipelines deployment...")
        fileio.makedirs(self.root_directory)

    def deprovision(self) -> None:
        """Deprovisions all local resources of the component."""

        if fileio.exists(self._log_file):
            fileio.remove(self._log_file)

        logger.info("Local kubeflow pipelines deployment deprovisioned.")

    def resume(self) -> None:
        """Resumes the local k3d cluster."""
        if self.is_running:
            logger.info("Local kubeflow pipelines deployment already running.")
            return

        self.start_kfp_metadata_daemon()
        self.wait_until_metadata_store_ready()

    def suspend(self) -> None:
        """Suspends the local k3d cluster."""
        if not self.is_running:
            logger.info("Local kubeflow pipelines deployment not running.")
            return

        self.stop_kfp_metadata_daemon()

    def start_kfp_metadata_daemon(self) -> None:
        """Starts a daemon process that forwards ports so the Kubeflow Pipelines
        Metadata MySQL database is accessible on the localhost."""

        command = [
            "kubectl",
            "--context",
            self.kubernetes_context,
            "--namespace",
            "kubeflow",
            "port-forward",
            "svc/metadata-grpc-service",
            f"{self.port}:8080",
        ]

        if sys.platform == "win32":
            logger.warning(
                "Daemon functionality not supported on Windows. "
                "In order to access the Kubeflow Pipelines Metadata locally, "
                "please run '%s' in a separate command line shell.",
                self.port,
                " ".join(command),
            )
        elif not networking_utils.port_available(self.port):
            raise ProvisioningError(
                f"Unable to port-forward Kubeflow Pipelines Metadata to local "
                f"port {self.port} because the port is occupied. In order to "
                f"access the Kubeflow Pipelines Metadata locally, please "
                f"change the metadata store configuration to use an available "
                f"port or stop the other process currently using the port."
            )
        else:
            from zenml.utils import daemon

            def _daemon_function() -> None:
                """Forwards the port of the Kubeflow Pipelines Metadata pod ."""
                subprocess.check_call(command)

            daemon.run_as_daemon(
                _daemon_function,
                pid_file=self._pid_file_path,
                log_file=self._log_file,
            )
            logger.info(
                "Started Kubeflow Pipelines Metadata daemon (check the daemon"
                "logs at %s in case you're not able to access the pipeline"
                "metadata).",
                self._log_file,
            )

    def stop_kfp_metadata_daemon(self) -> None:
        """Stops the KFP Metadata daemon process if it is running."""
        if fileio.exists(self._pid_file_path):
            if sys.platform == "win32":
                # Daemon functionality is not supported on Windows, so the PID
                # file won't exist. This if clause exists just for mypy to not
                # complain about missing functions
                pass
            else:
                from zenml.utils import daemon

                daemon.stop_daemon(self._pid_file_path)
                fileio.remove(self._pid_file_path)

    def wait_until_metadata_store_ready(
        self, timeout: int = DEFAULT_KFP_METADATA_DAEMON_TIMEOUT
    ) -> None:
        """Waits until the metadata store connection is ready, an irrecoverable
        error occurs or the timeout expires."""
        logger.info(
            "Waiting for the Kubeflow metadata store to be ready (this might "
            "take a few minutes)."
        )
        while True:
            try:
                # it doesn't matter what we call here as long as it exercises
                # the MLMD connection
                self.get_pipelines()
                break
            except Exception as e:
                logger.info(
                    "The Kubeflow metadata store is not ready yet. Waiting for "
                    "10 seconds..."
                )
                if timeout <= 0:
                    raise RuntimeError(
                        f"An unexpected error was encountered while waiting for the "
                        f"Kubeflow metadata store to be functional: {str(e)}"
                    ) from e
                timeout -= 10
                time.sleep(10)

        logger.info("The Kubeflow metadata store is functional.")
