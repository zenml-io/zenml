#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of Kubernetes metadata store."""

import os
import subprocess
import sys
import time
from typing import Any, ClassVar, Dict, Union

from kubernetes import client as k8s_client
from ml_metadata.proto import metadata_store_pb2
from ml_metadata.proto.metadata_store_pb2 import MySQLDatabaseConfig
from pydantic import root_validator

from zenml.exceptions import ProvisioningError, StackComponentInterfaceError
from zenml.integrations.kubernetes import KUBERNETES_METADATA_STORE_FLAVOR
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata_stores.base_metadata_store import BaseMetadataStore
from zenml.utils import io_utils, networking_utils

logger = get_logger(__name__)

DEFAULT_KUBERNETES_METADATA_DAEMON_TIMEOUT = 60
DEFAULT_KUBERNETES_METADATA_DAEMON_PID_FILE = "kubernetes_metadata_daemon.pid"
DEFAULT_KUBERNETES_METADATA_DAEMON_LOG_FILE = "kubernetes_metadata_daemon.log"

DEFAULT_KUBERNETES_MYSQL_HOST = "mysql"
DEFAULT_KUBERNETES_MYSQL_LOCAL_HOST = "127.0.0.1"
DEFAULT_KUBERNETES_MYSQL_PORT = 3306
DEFAULT_KUBERNETES_MYSQL_DATABASE = "mysql"
DEFAULT_KUBERNETES_MYSQL_USERNAME = "root"
DEFAULT_KUBERNETES_MYSQL_PASSWORD = ""
DEFAULT_KUBERNETES_MYSQL_SECRET = None


class KubernetesMetadataStore(BaseMetadataStore):
    """Kubernetes metadata store (MySQL database deployed in the cluster).

    Attributes:
        deployment_name: Name of the Kubernetes deployment and corresponding
            service/pod that will be created when calling `provision()`.
        kubernetes_context: Name of the Kubernetes context in which to deploy
            and provision the MySQL database.
        kubernetes_namespace: Name of the Kubernetes namespace.
            Defaults to "default".
        storage_capacity: Storage capacity of the metadata store.
            Defaults to `"10Gi"` (=10GB).
    """

    deployment_name: str
    kubernetes_context: str
    kubernetes_namespace: str = "zenml"
    storage_capacity: str = "10Gi"
    _k8s_core_api: k8s_client.CoreV1Api = None
    _k8s_apps_api: k8s_client.AppsV1Api = None

    FLAVOR: ClassVar[str] = KUBERNETES_METADATA_STORE_FLAVOR

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initiate the Pydantic object and initialize the Kubernetes clients.

        Args:
            *args: The positional arguments to pass to the Pydantic object.
            **kwargs: The keyword arguments to pass to the Pydantic object.
        """
        super().__init__(*args, **kwargs)
        self._initialize_k8s_clients()

    def _initialize_k8s_clients(self) -> None:
        """Initialize the Kubernetes clients."""
        kube_utils.load_kube_config(context=self.kubernetes_context)
        self._k8s_core_api = k8s_client.CoreV1Api()
        self._k8s_apps_api = k8s_client.AppsV1Api()

    @root_validator(skip_on_failure=False)
    def check_required_attributes(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic root_validator.

        This ensures that both `deployment_name` and `kubernetes_context` are
        set and raises an error with a custom error message otherwise.

        Args:
            values: Values passed to the Pydantic constructor.

        Raises:
            StackComponentInterfaceError: if either `deployment_name` or
                `kubernetes_context` is not defined.

        Returns:
            Values passed to the Pydantic constructor.
        """
        usage_note = (
            "Note: the `kubernetes` metadata store flavor is a special "
            "subtype of the `mysql` metadata store that deploys a fresh "
            "MySQL database within your Kubernetes cluster when running "
            "`zenml stack up`. "
            "If you already have a MySQL database running in your cluster "
            "(or elsewhere), simply use the `mysql` metadata store flavor "
            "instead."
        )

        for required_field in ("deployment_name", "kubernetes_context"):
            if required_field not in values:
                raise StackComponentInterfaceError(
                    f"Required field `{required_field}` missing for "
                    "`KubernetesMetadataStore`. " + usage_note
                )

        return values

    @property
    def deployment_exists(self) -> bool:
        """Check whether a MySQL deployment exists in the cluster.

        Returns:
            Whether a MySQL deployment exists in the cluster.
        """
        resp = self._k8s_apps_api.list_namespaced_deployment(
            namespace=self.kubernetes_namespace
        )
        for i in resp.items:
            if i.metadata.name == self.deployment_name:
                return True
        return False

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run.

        Checks whether the required MySQL deployment exists.

        Returns:
            True if the component provisioned resources to run.
        """
        return super().is_provisioned and self.deployment_exists

    @property
    def is_running(self) -> bool:
        """If the component is running.

        Returns:
            True if `is_provisioned` else False.
        """
        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            if not check_if_daemon_is_running(self._pid_file_path):
                return False
        else:
            # Daemon functionality is not supported on Windows, so the PID
            # file won't exist. This if clause exists just for mypy to not
            # complain about missing functions
            pass

        return self.is_provisioned

    def provision(self) -> None:
        """Provision the metadata store.

        Creates a deployment with a MySQL database running in it.
        """
        logger.info("Provisioning Kubernetes MySQL metadata store...")
        kube_utils.create_namespace(
            core_api=self._k8s_core_api, namespace=self.kubernetes_namespace
        )
        kube_utils.create_mysql_deployment(
            core_api=self._k8s_core_api,
            apps_api=self._k8s_apps_api,
            namespace=self.kubernetes_namespace,
            storage_capacity=self.storage_capacity,
            deployment_name=self.deployment_name,
        )

        # wait a bit, then make sure deployment pod is alive and running.
        logger.info("Trying to reach Kubernetes MySQL metadata store pod...")
        time.sleep(10)
        kube_utils.wait_pod(
            core_api=self._k8s_core_api,
            pod_name=self.pod_name,
            namespace=self.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_not_pending,
        )
        logger.info("Kubernetes MySQL metadata store pod is up and running.")

    def deprovision(self) -> None:
        """Deprovision the metadata store by deleting the MySQL deployment."""
        logger.info("Deleting Kubernetes MySQL metadata store...")
        self.suspend()
        kube_utils.delete_deployment(
            apps_api=self._k8s_apps_api,
            deployment_name=self.deployment_name,
            namespace=self.kubernetes_namespace,
        )

    # TODO: code duplication with kubeflow metadata store below.

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            self.FLAVOR,
            str(self.uuid),
        )

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(
            self.root_directory, DEFAULT_KUBERNETES_METADATA_DAEMON_PID_FILE
        )

    @property
    def _log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path to the daemon log file.
        """
        return os.path.join(
            self.root_directory, DEFAULT_KUBERNETES_METADATA_DAEMON_LOG_FILE
        )

    def resume(self) -> None:
        """Resumes the metadata store."""
        self.start_metadata_daemon()
        self.wait_until_metadata_store_ready(
            timeout=DEFAULT_KUBERNETES_METADATA_DAEMON_TIMEOUT
        )

    def suspend(self) -> None:
        """Suspends the metadata store."""
        self.stop_metadata_daemon()

    @property
    def pod_name(self) -> str:
        """Name of the Kubernetes pod where the MySQL database is deployed.

        Returns:
            Name of the Kubernetes pod.
        """
        pod_list = self._k8s_core_api.list_namespaced_pod(
            namespace=self.kubernetes_namespace,
            label_selector=f"app={self.deployment_name}",
        )
        return pod_list.items[0].metadata.name  # type: ignore[no-any-return]

    @property
    def host(self) -> str:
        """Get the MySQL host required to access the metadata store.

        This overwrites the MySQL host to use local host when
        running outside of the cluster so we can access the metadata store
        locally for post execution.

        Raises:
            RuntimeError: If the metadata store is not running.

        Returns:
            MySQL host.
        """
        if kube_utils.is_inside_kubernetes():
            return DEFAULT_KUBERNETES_MYSQL_HOST
        if not self.is_running:
            raise RuntimeError(
                "The Kubernetes metadata daemon is not running. Please run the "
                "following command to start it first:\n\n"
                "    'zenml metadata-store up'\n"
            )
        return DEFAULT_KUBERNETES_MYSQL_LOCAL_HOST

    @property
    def port(self) -> int:
        """Get the MySQL port required to access the metadata store.

        Returns:
            int: MySQL port.
        """
        return DEFAULT_KUBERNETES_MYSQL_PORT

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for the Kubernetes metadata store.

        Returns:
            The tfx metadata config.
        """
        config = MySQLDatabaseConfig(
            host=self.host,
            port=self.port,
            database=DEFAULT_KUBERNETES_MYSQL_DATABASE,
            user=DEFAULT_KUBERNETES_MYSQL_USERNAME,
            password=DEFAULT_KUBERNETES_MYSQL_PASSWORD,
        )
        connection_config = metadata_store_pb2.ConnectionConfig(mysql=config)
        return connection_config

    def start_metadata_daemon(self) -> None:
        """Starts a daemon process that forwards ports.

        This is so the MySQL database in the Kubernetes cluster is accessible
        on the localhost.

        Raises:
            ProvisioningError: if the daemon fails to start.
        """
        command = [
            "kubectl",
            "--context",
            self.kubernetes_context,
            "--namespace",
            self.kubernetes_namespace,
            "port-forward",
            f"svc/{self.deployment_name}",
            f"{self.port}:{self.port}",
        ]
        if sys.platform == "win32":
            logger.warning(
                "Daemon functionality not supported on Windows. "
                "In order to access the Kubernetes Metadata locally, "
                "please run '%s' in a separate command line shell.",
                self.port,
                " ".join(command),
            )
        elif not networking_utils.port_available(self.port):
            raise ProvisioningError(
                f"Unable to port-forward Kubernetes Metadata to local "
                f"port {self.port} because the port is occupied. In order to "
                f"access the Kubernetes Metadata locally, please "
                f"change the metadata store configuration to use an available "
                f"port or stop the other process currently using the port."
            )
        else:
            from zenml.utils import daemon

            def _daemon_function() -> None:
                """Forwards the port of the Kubernetes metadata store pod ."""
                subprocess.check_call(command)

            daemon.run_as_daemon(
                _daemon_function,
                pid_file=self._pid_file_path,
                log_file=self._log_file,
            )
            logger.info(
                "Started Kubernetes Metadata daemon (check the daemon"
                "logs at %s in case you're not able to access the pipeline"
                "metadata).",
                self._log_file,
            )

    def stop_metadata_daemon(self) -> None:
        """Stops the Kubernetes metadata daemon process if it is running."""
        if sys.platform != "win32" and fileio.exists(self._pid_file_path):
            from zenml.utils import daemon

            daemon.stop_daemon(self._pid_file_path)
            fileio.remove(self._pid_file_path)

    def wait_until_metadata_store_ready(self, timeout: int) -> None:
        """Waits until the metadata store connection is ready.

        Potentially an irrecoverable error could occur or the timeout could
        expire, so it checks for this.

        Args:
            timeout: The maximum time to wait for the metadata store to be
                ready.

        Raises:
            RuntimeError: if the metadata store is not ready after the timeout
        """
        logger.info(
            "Waiting for the Kubernetes metadata store to be ready (this "
            "might take a few minutes)."
        )
        while True:
            try:
                # it doesn't matter what we call here as long as it exercises
                # the MLMD connection
                self.get_pipelines()
                break
            except Exception as e:
                logger.info(
                    "The Kubernetes metadata store is not ready yet. Waiting "
                    "for 10 seconds..."
                )
                if timeout <= 0:
                    raise RuntimeError(
                        f"An unexpected error was encountered while waiting "
                        f"for the Kubernetes metadata store to be functional: "
                        f"{str(e)}"
                    ) from e
                timeout -= 10
                time.sleep(10)

        logger.info("The Kubernetes metadata store is functional.")
