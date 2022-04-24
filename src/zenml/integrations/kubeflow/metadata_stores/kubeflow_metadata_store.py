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
import zenml.io.utils

from typing import ClassVar, Union

from kubernetes import config as k8s_config
from ml_metadata.proto import metadata_store_pb2

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata_stores import MySQLMetadataStore
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.utils import networking_utils
from zenml.utils.daemon import check_if_daemon_is_running

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


@register_stack_component_class
class KubeflowMetadataStore(MySQLMetadataStore):
    """Kubeflow MySQL backend for ZenML metadata store."""

    host: str = "127.0.0.1"
    port: int = 3306
    database: str = "metadb"
    username: str = "root"
    password: str = ""

    # Class Configuration
    FLAVOR: ClassVar[str] = "kubeflow"

    @property
    def upgrade_migration_enabled(self) -> bool:
        """Return False to disable automatic database schema migration."""
        return False

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for the kubeflow metadata store."""
        if inside_kfp_pod():
            connection_config = metadata_store_pb2.MetadataStoreClientConfig()
            connection_config.host = os.environ["METADATA_GRPC_SERVICE_HOST"]
            connection_config.port = int(
                os.environ["METADATA_GRPC_SERVICE_PORT"]
            )
            return connection_config
        else:
            return super().get_tfx_metadata_config()

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning
        this orchestrator."""
        return os.path.join(
            zenml.io.utils.get_global_config_directory(),
            "kubeflow",
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
            if not check_if_daemon_is_running(self._pid_file_path):
                return False
        else:
            ...

        try:
            self.get_pipelines()
        except Exception as e:
            logger.error(
                "Error while checking if kubeflow metadata store is running: %s",
                e,
            )
            return False
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
            "--namespace",
            "kubeflow",
            "port-forward",
            "svc/mysql",
            f"{self.port}:3306",
        ]

        if not networking_utils.port_available(self.port):
            logger.warning(
                "Unable to port-forward Kubeflow Pipelines Metadata to local "
                "port %d because the port is occupied. In order to access the "
                "Kubeflow Pipelines Metadata locally, please change the metadata "
                "store configuration to use a free port.",
                self.port,
            )
        elif sys.platform == "win32":
            logger.warning(
                "Daemon functionality not supported on Windows. "
                "In order to access the Kubeflow Pipelines Metadata locally, "
                "please run '%s' in a separate command line shell.",
                self.port,
                " ".join(command),
            )
        else:
            from zenml.utils import daemon

            def _daemon_function() -> None:
                """Port-forwards the Kubeflow Pipelines Metadata pod."""
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
