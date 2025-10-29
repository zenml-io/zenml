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
"""Shared mixin for Kubernetes-based stack components."""

from typing import TYPE_CHECKING, List, Optional, Tuple

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field

from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

__all__ = [
    "KubernetesComponentConfig",
    "KubernetesComponentMixin",
]


class KubernetesComponentConfig(BaseModel):
    """Base config for Kubernetes-based components.

    Components that inherit from KubernetesComponentMixin should
    have their config class inherit from this.

    Note: kubernetes_namespace is intentionally not included here
    as different components have different default values and requirements.
    Subclasses should define it themselves.
    """

    kubernetes_context: Optional[str] = Field(
        None,
        description="Name of a Kubernetes context to run pipelines in. "
        "If the stack component is linked to a Kubernetes service connector, "
        "this field is ignored. Otherwise, it is mandatory.",
    )
    incluster: bool = Field(
        False,
        description="If `True`, the orchestrator will run the pipeline inside the "
        "same cluster in which it itself is running. This requires the client "
        "to run in a Kubernetes pod itself. If set, the `kubernetes_context` "
        "config option is ignored. If the stack component is linked to a "
        "Kubernetes service connector, this field is ignored.",
    )
    kubernetes_namespace: str = Field(
        "zenml",
        description="Name of the Kubernetes namespace to be used. "
        "If not provided, `zenml` namespace will be used.",
    )

    @property
    def is_local(self) -> bool:
        """Check if this is a local Kubernetes cluster.

        Can be overridden by subclasses for custom logic.

        Returns:
            True if using a local Kubernetes cluster, False otherwise.
        """
        # Check if context indicates a local cluster
        if self.kubernetes_context:
            local_context_indicators = [
                "k3d-",
                "kind-",
                "minikube",
                "docker-desktop",
                "colima",
                "rancher-desktop",
            ]
            context_lower = self.kubernetes_context.lower()
            return any(
                indicator in context_lower
                for indicator in local_context_indicators
            )
        return False


class KubernetesComponentMixin:
    """Mixin for Kubernetes-based stack components.

    Provides common functionality for components that interact with
    Kubernetes clusters, including client management, context validation,
    and service account creation.

    Components using this mixin should:
    1. Have a config class that inherits from KubernetesComponentConfig
    2. Initialize `_k8s_client` to None in their __init__
    3. Call mixin methods for Kubernetes operations
    """

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def config(self) -> KubernetesComponentConfig:
        """Get the component config.

        This property must be implemented by subclasses.

        Raises:
            NotImplementedError: If the subclass does not implement the config property.
        """
        raise NotImplementedError(
            "Subclasses must implement the config property"
        )

    @property
    def name(self) -> str:
        """Get the component name.

        This property must be implemented by subclasses.

        Raises:
            NotImplementedError: If the subclass does not implement the name property.
        """
        raise NotImplementedError(
            "Subclasses must implement the name property"
        )

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Get authenticated Kubernetes client.

        This method handles:
        - In-cluster authentication
        - Service connector authentication
        - Local kubeconfig authentication
        - Client caching and expiration

        Args:
            incluster: Whether to use in-cluster config. Overrides
                the config setting if provided.

        Returns:
            Authenticated Kubernetes API client.

        Raises:
            RuntimeError: If connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        connector_has_expired = self.connector_has_expired()  # type: ignore[attr-defined]
        if self._k8s_client and not connector_has_expired:
            return self._k8s_client

        connector = self.get_connector()  # type: ignore[attr-defined]
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
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def k8s_core_api(self) -> k8s_client.CoreV1Api:
        """Get Kubernetes Core V1 API client.

        Returns:
            Kubernetes Core V1 API client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    @property
    def k8s_apps_api(self) -> k8s_client.AppsV1Api:
        """Get Kubernetes Apps V1 API client.

        Returns:
            Kubernetes Apps V1 API client.
        """
        return k8s_client.AppsV1Api(self.get_kube_client())

    @property
    def k8s_batch_api(self) -> k8s_client.BatchV1Api:
        """Get Kubernetes Batch V1 API client.

        Returns:
            Kubernetes Batch V1 API client.
        """
        return k8s_client.BatchV1Api(self.get_kube_client())

    @property
    def k8s_rbac_api(self) -> k8s_client.RbacAuthorizationV1Api:
        """Get Kubernetes RBAC Authorization V1 API client.

        Returns:
            Kubernetes RBAC Authorization V1 API client.
        """
        return k8s_client.RbacAuthorizationV1Api(self.get_kube_client())

    @property
    def k8s_networking_api(self) -> k8s_client.NetworkingV1Api:
        """Get Kubernetes Networking V1 API client.

        Returns:
            Kubernetes Networking V1 API client.
        """
        return k8s_client.NetworkingV1Api(self.get_kube_client())

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get list of configured Kubernetes contexts and the active context.

        Returns:
            Tuple of (context_names, active_context_name).

        Raises:
            RuntimeError: If Kubernetes configuration cannot be loaded.
        """
        try:
            contexts, active_context = k8s_config.list_kube_config_contexts()
        except k8s_config.config_exception.ConfigException as e:
            raise RuntimeError(
                "Could not load the Kubernetes configuration"
            ) from e

        context_names = [c["name"] for c in contexts]
        active_context_name = active_context["name"]
        return context_names, active_context_name

    def validate_kubernetes_context(
        self, stack: "Stack", component_type: str
    ) -> Tuple[bool, str]:
        """Validate Kubernetes context configuration.

        Args:
            stack: The stack to validate.
            component_type: Type of component (e.g., "orchestrator", "deployer").

        Returns:
            Tuple of (is_valid, error_message).
        """
        container_registry = stack.container_registry
        assert container_registry is not None

        kubernetes_context = self.config.kubernetes_context
        msg = f"'{self.name}' Kubernetes {component_type} error: "

        if not self.get_connector():  # type: ignore[attr-defined]
            if kubernetes_context:
                try:
                    contexts, active_context = self.get_kubernetes_contexts()

                    if kubernetes_context not in contexts:
                        return False, (
                            f"{msg}could not find a Kubernetes context named "
                            f"'{kubernetes_context}' in the local "
                            "Kubernetes configuration. Please make sure that "
                            "the Kubernetes cluster is running and that the "
                            "kubeconfig file is configured correctly. To list "
                            "all configured contexts, run:\n\n"
                            "  `kubectl config get-contexts`\n"
                        )
                    if kubernetes_context != active_context:
                        logger.warning(
                            f"{msg}the Kubernetes context '{kubernetes_context}' "
                            f"configured for the Kubernetes {component_type} is not "
                            f"the same as the active context in the local Kubernetes "
                            f"configuration. To set the active context, run:\n\n"
                            f"  `kubectl config use-context {kubernetes_context}`\n"
                        )
                except Exception:
                    # If we can't load kube config, that's okay - might be in-cluster
                    pass
            elif self.config.incluster:
                # No service connector or kubernetes_context needed when
                # running from within a Kubernetes cluster
                pass
            else:
                return False, (
                    f"{msg}you must either link this {component_type} to a "
                    "Kubernetes service connector (see the 'zenml "
                    f"{component_type} connect' CLI command), explicitly set "
                    "the `kubernetes_context` attribute to the name of the "
                    "Kubernetes config context pointing to the cluster "
                    "where you would like to run operations, or set the "
                    "`incluster` attribute to `True`."
                )

        # If the component is remote, the container registry must also be remote
        if not self.config.is_local and container_registry.config.is_local:
            return False, (
                f"{msg}the Kubernetes {component_type} is configured to "
                "run in a remote Kubernetes cluster but the "
                f"'{container_registry.name}' container registry URI "
                f"'{container_registry.config.uri}' points to a local "
                f"container registry. Please ensure that you use a remote "
                f"container registry with a remote Kubernetes {component_type}."
            )

        return True, ""

    def ensure_namespace_exists(self, namespace: str) -> None:
        """Ensure a Kubernetes namespace exists.

        Args:
            namespace: The namespace name.

        Raises:
            RuntimeError: If namespace creation fails due to permissions
                or other non-conflict errors.
        """
        try:
            kube_utils.create_namespace(
                core_api=self.k8s_core_api,
                namespace=namespace,
            )
            logger.debug(f"Created namespace '{namespace}'.")
        except ApiException as e:
            # 409 Conflict means namespace already exists, which is fine
            if e.status == 409:
                logger.debug(f"Namespace '{namespace}' already exists.")
            else:
                # Re-raise RBAC/permission errors or other API failures
                raise RuntimeError(
                    f"Failed to ensure namespace '{namespace}' exists: {e}. "
                    f"This may be due to insufficient permissions (RBAC) or "
                    f"cluster configuration issues."
                ) from e

    def create_or_get_service_account(
        self,
        service_account_name: str,
        namespace: str,
        role_binding_name: str = "zenml-edit",
    ) -> str:
        """Create or get a Kubernetes service account with edit permissions.

        Args:
            service_account_name: Name of the service account.
            namespace: Kubernetes namespace.
            role_binding_name: Name of the role binding.

        Returns:
            The service account name.
        """
        kube_utils.create_edit_service_account(
            core_api=self.k8s_core_api,
            rbac_api=self.k8s_rbac_api,
            service_account_name=service_account_name,
            namespace=namespace,
            role_binding_name=role_binding_name,
        )
        return service_account_name
