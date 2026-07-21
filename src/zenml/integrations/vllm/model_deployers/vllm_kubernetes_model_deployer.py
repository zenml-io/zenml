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
"""Implementation of the Kubernetes vLLM Model Deployer."""

import os
from typing import ClassVar, Dict, Optional, Type, cast
from uuid import UUID

from kubernetes import client as k8s_client

from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.k8s_applier import KubernetesApplier
from zenml.integrations.vllm.flavors.vllm_kubernetes_model_deployer_flavor import (
    KubernetesVLLMModelDeployerConfig,
    KubernetesVLLMModelDeployerFlavor,
)
from zenml.integrations.vllm.services.vllm_deployment import (
    VLLM_HEALTHCHECK_URL_PATH,
    VLLM_PREDICTION_URL_PATH,
)
from zenml.integrations.vllm.services.vllm_kubernetes_deployment import (
    VLLMKubernetesDeploymentService,
    VLLMKubernetesServiceConfig,
)
from zenml.logger import get_logger
from zenml.model_deployers import BaseModelDeployer, BaseModelDeployerFlavor
from zenml.services.service import BaseService, ServiceConfig

logger = get_logger(__name__)

DEFAULT_VLLM_KUBERNETES_DEPLOYMENT_START_STOP_TIMEOUT = 300


class KubernetesVLLMModelDeployer(BaseModelDeployer):
    """Kubernetes vLLM model deployer stack component implementation."""

    NAME: ClassVar[str] = "vLLM Kubernetes"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        KubernetesVLLMModelDeployerFlavor
    )

    _k8s_client: Optional[k8s_client.ApiClient] = None
    _applier: Optional[KubernetesApplier] = None

    @property
    def config(self) -> KubernetesVLLMModelDeployerConfig:
        """Returns the `KubernetesVLLMModelDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesVLLMModelDeployerConfig, self._config)

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Args:
            incluster: Whether to use the in-cluster config or not. Overrides
                the `incluster` setting in the config.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.

        Returns:
            The Kubernetes API client.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            try:
                kube_utils.load_kube_config(
                    incluster=incluster,
                )
                self._k8s_client = k8s_client.ApiClient()
                return self._k8s_client
            except Exception as e:
                if self.connector:
                    message = (
                        "Falling back to using the linked service connector "
                        "configuration."
                    )
                elif self.config.kubernetes_context:
                    message = (
                        f"Falling back to using the configured "
                        f"'{self.config.kubernetes_context}' kubernetes context."
                    )
                else:
                    raise RuntimeError(
                        f"The model deployer failed to load the in-cluster "
                        f"Kubernetes configuration and there is no service "
                        f"connector or kubernetes_context to fall back to: {e}"
                    ) from e

                logger.debug(
                    f"Could not load the in-cluster Kubernetes configuration: "
                    f"{e}. {message}"
                )

        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def k8s_applier(self) -> KubernetesApplier:
        """Get or create the Kubernetes Applier instance.

        Returns:
            Kubernetes Applier instance.
        """
        if self.connector_has_expired():
            self._applier = None

        if not self._applier:
            self._applier = KubernetesApplier(
                api_client=self.get_kube_client()
            )
        return self._applier

    @staticmethod
    def get_model_server_info(  # type: ignore[override]
        service_instance: "VLLMKubernetesDeploymentService",
    ) -> Dict[str, Optional[str]]:
        """Return implementation specific information on the model server.

        Args:
            service_instance: vLLM Kubernetes deployment service object.

        Returns:
            A dictionary containing the model server information.
        """
        base_url = service_instance.service_url
        return {
            "PREDICTION_URL": os.path.join(base_url, VLLM_PREDICTION_URL_PATH)
            if base_url
            else None,
            "HEALTH_CHECK_URL": os.path.join(
                base_url, VLLM_HEALTHCHECK_URL_PATH
            )
            if base_url
            else None,
            "MODEL": service_instance.config.model,
            "IMAGE": service_instance.image,
            "NAMESPACE": service_instance.namespace,
            "DEPLOYMENT_NAME": service_instance.deployment_name,
            "SERVICE_TYPE": str(service_instance.service_type),
        }

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_VLLM_KUBERNETES_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Create a new vLLM Kubernetes deployment service.

        Args:
            id: the UUID of the model server to deploy.
            config: the configuration of the model to be deployed with vLLM
                on Kubernetes.
            timeout: the timeout in seconds to wait for the vLLM server to
                be provisioned and successfully started. If set to 0, the
                method will return immediately after the vLLM server is
                provisioned, without waiting for it to fully start.

        Returns:
            The ZenML vLLM Kubernetes deployment service object that can be
            used to interact with the remote vLLM server.
        """
        config = cast(VLLMKubernetesServiceConfig, config)

        config.namespace = config.namespace or self.config.kubernetes_namespace
        config.image = config.image or self.config.default_image
        config.service_type = (
            config.service_type or self.config.default_service_type
        )
        if not config.hf_token and not config.existing_hf_secret:
            config.hf_token = self.config.hf_token

        service = VLLMKubernetesDeploymentService(uuid=id, config=config)
        logger.info(
            f"Creating a new vLLM Kubernetes deployment service: {service}"
        )
        service.start(timeout=timeout)

        return service

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_VLLM_KUBERNETES_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> BaseService:
        """Stop a vLLM Kubernetes model server.

        Args:
            service: The service to stop.
            timeout: timeout in seconds to wait for the service to stop.
            force: if True, force the service to stop.

        Raises:
            NotImplementedError: stopping vLLM Kubernetes model servers is
                not supported.

        Returns:
            The stopped service.
        """
        raise NotImplementedError(
            "Stopping vLLM Kubernetes model servers is not implemented. Try "
            "deleting the vLLM Kubernetes model server instead."
        )

    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_VLLM_KUBERNETES_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        """Start a vLLM Kubernetes model deployment server.

        Args:
            service: The service to start.
            timeout: timeout in seconds to wait for the service to become
                active. If set to 0, the method will return immediately
                after provisioning the service, without waiting for it to
                become active.

        Raises:
            NotImplementedError: since we don't support starting vLLM
                Kubernetes model servers.

        Returns:
            The started service.
        """
        raise NotImplementedError(
            "Starting vLLM Kubernetes model servers is not implemented"
        )

    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_VLLM_KUBERNETES_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> None:
        """Delete a vLLM Kubernetes model deployment server.

        Args:
            service: The service to delete.
            timeout: timeout in seconds to wait for the service to stop. If
                set to 0, the method will return immediately after
                deprovisioning the service, without waiting for it to stop.
            force: if True, force the service to stop.
        """
        service = cast(VLLMKubernetesDeploymentService, service)
        service.stop(timeout=timeout, force=force)
