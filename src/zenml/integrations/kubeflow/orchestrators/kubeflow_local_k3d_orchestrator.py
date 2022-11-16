# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

# Minor parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the kubeflow dag runner implementation of tfx
"""Implementation of the Kubeflow orchestrator."""
import os
import sys
from typing import Optional, cast
from uuid import UUID

import kfp

from zenml.artifact_stores import LocalArtifactStore
from zenml.client import Client
from zenml.exceptions import ProvisioningError
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    DEFAULT_KFP_UI_PORT,
    KubeflowLocalK3DOrchestratorConfig,
    KubeflowOrchestratorSettings,
)
from zenml.integrations.kubeflow.orchestrators import local_deployment_utils
from zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator import (
    KubeflowOrchestrator,
)
from zenml.integrations.kubeflow.orchestrators.local_deployment_utils import (
    KFP_VERSION,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, networking_utils

logger = get_logger(__name__)

KFP_POD_LABELS = {
    "add-pod-env": "true",
    "pipelines.kubeflow.org/pipeline-sdk-type": "zenml",
}

ENV_KFP_RUN_ID = "KFP_RUN_ID"


class KubeflowLocalK3DOrchestrator(KubeflowOrchestrator):
    """Orchestrator responsible for running pipelines using Kubeflow locally with K3D."""

    @property
    def config(self) -> KubeflowLocalK3DOrchestratorConfig:
        """Returns the `KubeflowLocalK3DOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubeflowLocalK3DOrchestratorConfig, self._config)

    @staticmethod
    def _get_k3d_cluster_name(uuid: UUID) -> str:
        """Returns the k3d cluster name corresponding to the orchestrator UUID.

        Args:
            uuid: The UUID of the orchestrator.

        Returns:
            The k3d cluster name.
        """
        # k3d only allows cluster names with up to 32 characters; use the
        # first 8 chars of the orchestrator UUID as identifier
        return f"zenml-kubeflow-{str(uuid)[:8]}"

    @staticmethod
    def _get_k3d_kubernetes_context(uuid: UUID) -> str:
        """Gets the k3d kubernetes context.

        Args:
            uuid: The UUID of the orchestrator.

        Returns:
            The name of the kubernetes context associated with the k3d
                cluster managed locally by ZenML corresponding to the orchestrator UUID.
        """
        return f"k3d-{KubeflowLocalK3DOrchestrator._get_k3d_cluster_name(uuid)}"

    @property
    def is_local(self) -> bool:
        """Checks if the KFP orchestrator is running locally.

        Returns:
            `True` if the KFP orchestrator is running locally (i.e. in
            the local k3d cluster managed by ZenML).
        """
        return True

    @property
    def kubernetes_context(self) -> str:
        """Returns the kubernetes context associated with the local orchestrator.

        Returns:
            The name of the kubernetes context associated with the k3d
        """
        return self._get_k3d_kubernetes_context(self.id)

    def _get_kfp_client(
        self,
        settings: Optional[KubeflowOrchestratorSettings] = None,
    ) -> kfp.Client:
        """Creates a KFP client instance.

        Args:
            settings: Optional settings which can be used to
                configure the client instance.

        Returns:
            A KFP client instance.
        """
        client_args = {
            "kube_context": self.config.kubernetes_context,
        }

        if settings:
            client_args.update(settings.client_args)

        # The host and namespace are stack component configurations that refer
        # to the Kubeflow deployment. We don't want these overwritten on a
        # run by run basis by user settings
        client_args["host"] = self.config.kubeflow_hostname
        client_args["namespace"] = self.config.kubeflow_namespace

        return kfp.Client(**client_args)

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.root_directory, "kubeflow_daemon.pid")

    @property
    def log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path of the daemon log file.
        """
        return os.path.join(self.root_directory, "kubeflow_daemon.log")

    @property
    def _k3d_cluster_name(self) -> str:
        """Returns the K3D cluster name.

        Returns:
            The K3D cluster name.
        """
        return self._get_k3d_cluster_name(self.id)

    def _get_k3d_registry_name(self, port: int) -> str:
        """Returns the K3D registry name.

        Args:
            port: Port of the registry.

        Returns:
            The registry name.
        """
        return f"k3d-zenml-kubeflow-registry.localhost:{port}"

    @property
    def _k3d_registry_config_path(self) -> str:
        """Returns the path to the K3D registry config yaml.

        Returns:
            str: Path to the K3D registry config yaml.
        """
        return os.path.join(self.root_directory, "k3d_registry.yaml")

    def _get_kfp_ui_daemon_port(self) -> int:
        """Port to use for the KFP UI daemon.

        Returns:
            Port to use for the KFP UI daemon.
        """
        port = self.config.kubeflow_pipelines_ui_port
        if port == DEFAULT_KFP_UI_PORT and not networking_utils.port_available(
            port
        ):
            # if the user didn't specify a specific port and the default
            # port is occupied, fallback to a random open port
            port = networking_utils.find_available_port()
        return port

    def list_manual_setup_steps(
        self, container_registry_name: str, container_registry_path: str
    ) -> None:
        """Logs manual steps needed to setup the Kubeflow local orchestrator.

        Args:
            container_registry_name: Name of the container registry.
            container_registry_path: Path to the container registry.
        """
        if not self.is_local:
            # Make sure we're not telling users to deploy Kubeflow on their
            # remote clusters
            logger.warning(
                "This Kubeflow orchestrator is configured to use a non-local "
                f"Kubernetes context {self.kubernetes_context}. Manually "
                f"deploying Kubeflow Pipelines is only possible for local "
                f"Kubeflow orchestrators."
            )
            return

        global_config_dir_path = io_utils.get_global_config_directory()
        kubeflow_commands = [
            f"> k3d cluster create {self._k3d_cluster_name} --image {local_deployment_utils.K3S_IMAGE_NAME} --registry-create {container_registry_name} --registry-config {container_registry_path} --volume {global_config_dir_path}:{global_config_dir_path}\n",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} wait --timeout=60s --for condition=established crd/applications.app.k8s.io",
            f"> kubectl --context {self.kubernetes_context} apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref={KFP_VERSION}&timeout=5m",
            f"> kubectl --context {self.kubernetes_context} --namespace kubeflow port-forward svc/ml-pipeline-ui {self.config.kubeflow_pipelines_ui_port}:80",
        ]

        logger.info(
            "If you wish to spin up this Kubeflow local orchestrator manually, "
            "please enter the following commands:\n"
        )
        logger.info("\n".join(kubeflow_commands))

    @property
    def is_provisioned(self) -> bool:
        """Returns if a local k3d cluster for this orchestrator exists.

        Returns:
            True if a local k3d cluster exists, False otherwise.
        """
        if not local_deployment_utils.check_prerequisites(
            skip_k3d=self.config.skip_cluster_provisioning or not self.is_local,
            skip_kubectl=self.config.skip_cluster_provisioning
            and self.config.skip_ui_daemon_provisioning,
        ):
            # if any prerequisites are missing there is certainly no
            # local deployment running
            return False

        return self.is_cluster_provisioned

    @property
    def is_running(self) -> bool:
        """Checks if the local k3d cluster and UI daemon are both running.

        Returns:
            True if the local k3d cluster and UI daemon for this orchestrator are both running.
        """
        return (
            self.is_provisioned
            and self.is_cluster_running
            and self.is_daemon_running
        )

    @property
    def is_suspended(self) -> bool:
        """Checks if the local k3d cluster and UI daemon are both stopped.

        Returns:
            True if the cluster and daemon for this orchestrator are both stopped, False otherwise.
        """
        return (
            self.is_provisioned
            and (
                self.config.skip_cluster_provisioning
                or not self.is_cluster_running
            )
            and (
                self.config.skip_ui_daemon_provisioning
                or not self.is_daemon_running
            )
        )

    @property
    def is_cluster_provisioned(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is provisioned.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.

        Returns:
            True if the local k3d cluster is provisioned, False otherwise.
        """
        if self.config.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_exists(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_cluster_running(self) -> bool:
        """Returns if the local k3d cluster for this orchestrator is running.

        For remote (i.e. not managed by ZenML) Kubeflow Pipelines installations,
        this always returns True.

        Returns:
            True if the local k3d cluster is running, False otherwise.
        """
        if self.config.skip_cluster_provisioning or not self.is_local:
            return True
        return local_deployment_utils.k3d_cluster_running(
            cluster_name=self._k3d_cluster_name
        )

    @property
    def is_daemon_running(self) -> bool:
        """Returns if the local Kubeflow UI daemon for this orchestrator is running.

        Returns:
            True if the daemon is running, False otherwise.
        """
        if self.config.skip_ui_daemon_provisioning:
            return True

        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            return check_if_daemon_is_running(self._pid_file_path)
        else:
            return True

    def provision(self) -> None:
        """Provisions a local Kubeflow Pipelines deployment.

        Raises:
            ProvisioningError: If the provisioning fails.
        """
        if self.config.skip_cluster_provisioning:
            return

        if self.is_running:
            logger.info(
                "Found already existing local Kubeflow Pipelines deployment. "
                "If there are any issues with the existing deployment, please "
                "run 'zenml stack down --force' to delete it."
            )
            return

        if not local_deployment_utils.check_prerequisites():
            raise ProvisioningError(
                "Unable to provision local Kubeflow Pipelines deployment: "
                "Please install 'k3d' and 'kubectl' and try again."
            )

        container_registry = Client().active_stack.container_registry

        # should not happen, because the stack validation takes care of this,
        # but just in case
        assert container_registry is not None

        fileio.makedirs(self.root_directory)

        if not self.is_local:
            # don't provision any resources if using a remote KFP installation
            return

        logger.info("Provisioning local Kubeflow Pipelines deployment...")

        container_registry_port = int(
            container_registry.config.uri.split(":")[-1]
        )
        container_registry_name = self._get_k3d_registry_name(
            port=container_registry_port
        )
        local_deployment_utils.write_local_registry_yaml(
            yaml_path=self._k3d_registry_config_path,
            registry_name=container_registry_name,
            registry_uri=container_registry.config.uri,
        )

        try:
            local_deployment_utils.create_k3d_cluster(
                cluster_name=self._k3d_cluster_name,
                registry_name=container_registry_name,
                registry_config_path=self._k3d_registry_config_path,
            )
            kubernetes_context = self.kubernetes_context

            # will never happen, but mypy doesn't know that
            assert kubernetes_context is not None

            local_deployment_utils.deploy_kubeflow_pipelines(
                kubernetes_context=kubernetes_context
            )

            artifact_store = Client().active_stack.artifact_store
            if isinstance(artifact_store, LocalArtifactStore):
                local_deployment_utils.add_hostpath_to_kubeflow_pipelines(
                    kubernetes_context=kubernetes_context,
                    local_path=artifact_store.path,
                )
        except Exception as e:
            logger.error(e)
            logger.error(
                "Unable to spin up local Kubeflow Pipelines deployment."
            )

            self.list_manual_setup_steps(
                container_registry_name, self._k3d_registry_config_path
            )
            self.deprovision()

    def deprovision(self) -> None:
        """Deprovisions a local Kubeflow Pipelines deployment."""
        if self.config.skip_cluster_provisioning:
            return

        if (
            not self.config.skip_ui_daemon_provisioning
            and self.is_daemon_running
        ):
            local_deployment_utils.stop_kfp_ui_daemon(
                pid_file_path=self._pid_file_path
            )

        if self.is_local:
            # don't deprovision any resources if using a remote KFP installation
            local_deployment_utils.delete_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )

            logger.info("Local kubeflow pipelines deployment deprovisioned.")

        if fileio.exists(self.log_file):
            fileio.remove(self.log_file)

    def resume(self) -> None:
        """Resumes the local k3d cluster.

        Raises:
            ProvisioningError: If the k3d cluster is not provisioned.
        """
        if self.is_running:
            logger.info("Local kubeflow pipelines deployment already running.")
            return

        if not self.is_provisioned:
            raise ProvisioningError(
                "Unable to resume local kubeflow pipelines deployment: No "
                "resources provisioned for local deployment."
            )

        kubernetes_context = self.kubernetes_context

        # will never happen, but mypy doesn't know that
        assert kubernetes_context is not None

        if (
            not self.config.skip_cluster_provisioning
            and self.is_local
            and not self.is_cluster_running
        ):
            # don't resume any resources if using a remote KFP installation
            local_deployment_utils.start_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )

            local_deployment_utils.wait_until_kubeflow_pipelines_ready(
                kubernetes_context=kubernetes_context
            )

        if not self.is_daemon_running:
            local_deployment_utils.start_kfp_ui_daemon(
                pid_file_path=self._pid_file_path,
                log_file_path=self.log_file,
                port=self._get_kfp_ui_daemon_port(),
                kubernetes_context=kubernetes_context,
            )

    def suspend(self) -> None:
        """Suspends the local k3d cluster."""
        if not self.is_provisioned:
            logger.info("Local kubeflow pipelines deployment not provisioned.")
            return

        if (
            not self.config.skip_ui_daemon_provisioning
            and self.is_daemon_running
        ):
            local_deployment_utils.stop_kfp_ui_daemon(
                pid_file_path=self._pid_file_path
            )

        if (
            not self.config.skip_cluster_provisioning
            and self.is_local
            and self.is_cluster_running
        ):
            # don't suspend any resources if using a remote KFP installation
            local_deployment_utils.stop_k3d_cluster(
                cluster_name=self._k3d_cluster_name
            )
