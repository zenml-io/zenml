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
"""Kubernetes resource applier."""

import time
from typing import Any, Callable, Dict, List, Optional

import yaml
from kubernetes import client as k8s_client
from kubernetes import dynamic
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.exceptions import ResourceNotFoundError

from zenml.logger import get_logger

logger = get_logger(__name__)


class KubernetesApplier:
    """Kubernetes resource applier.

    This class uses the Kubernetes Dynamic Client to apply ANY resource type
    WITHOUT needing hardcoded mappings! The K8s API server tells us everything
    we need to know about each resource type through API discovery.

    Example:
        applier = KubernetesApplier(api_client=k8s_client.ApiClient())

        # Apply YAML directly - no need to know the type!
        applier.apply_yaml(yaml_string, dry_run=False)

        # Or apply a K8s object
        applier.apply_resource(k8s_deployment, dry_run=False)

        # Delete by name/namespace/kind
        applier.delete_resource("my-app", "default", "Deployment", "apps/v1")

    How it works:
    1. Parses YAML to extract kind and apiVersion
    2. Uses dynamic client to discover the resource API
    3. Automatically handles create-or-update logic
    4. Works for ANY K8s resource - built-in or CRDs!
    """

    def __init__(self, api_client: k8s_client.ApiClient):
        """Initialize the applier with a Kubernetes API client.

        Args:
            api_client: Kubernetes API client (can be from connector or kubeconfig).
        """
        self.api_client = api_client
        self.dynamic_client = dynamic.DynamicClient(api_client)

    def apply_yaml(
        self,
        yaml_content: str,
        dry_run: bool = False,
    ) -> Any:
        """Apply Kubernetes resource from YAML string.

        This is the TRULY GENERIC method - it works for ANY resource type
        without needing to know what it is ahead of time!

        Args:
            yaml_content: YAML string containing the resource definition.
            dry_run: If True, validate without actually creating/updating.

        Returns:
            The applied resource object.

        Raises:
            ValueError: If YAML is invalid or missing required fields.
            ApiException: If the operation fails.
        """
        try:
            resource_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        if not isinstance(resource_dict, dict):
            raise ValueError("YAML must contain a dictionary")

        # Extract required fields
        kind = resource_dict.get("kind")
        api_version = resource_dict.get("apiVersion")

        if not kind or not api_version:
            raise ValueError(
                "Resource must have 'kind' and 'apiVersion' fields. "
                f"Got: kind={kind}, apiVersion={api_version}"
            )

        metadata = resource_dict.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")

        if not name:
            raise ValueError("Resource must have 'metadata.name' field")

        # Use dynamic client to discover and apply the resource
        try:
            # Get the API resource for this kind
            api_resource = self.dynamic_client.resources.get(
                api_version=api_version,
                kind=kind,
            )
        except ResourceNotFoundError as e:
            raise ValueError(
                f"Unknown resource type: {kind} (apiVersion: {api_version}). "
                f"This might be a CRD that's not installed in your cluster."
            ) from e

        # Check if this resource is namespaced or cluster-scoped
        is_namespaced = api_resource.namespaced

        # For namespaced resources without a namespace, default to "default"
        if is_namespaced and not namespace:
            namespace = "default"
            # Update the resource dict to include the namespace
            if "metadata" not in resource_dict:
                resource_dict["metadata"] = {}
            resource_dict["metadata"]["namespace"] = namespace

        # Only use namespace for namespaced resources
        get_kwargs = {"name": name}
        if is_namespaced:
            get_kwargs["namespace"] = namespace

        dry_run_param = "All" if dry_run else None

        try:
            # Try to get existing resource (just to check if it exists)
            api_resource.get(**get_kwargs)

            # Resource exists - update it
            location = (
                f"in {namespace}" if is_namespaced else "(cluster-scoped)"
            )
            logger.info(
                f"{'[DRY-RUN] ' if dry_run else ''}Updating {kind} {name} {location}"
            )

            # Server-side apply (the modern K8s way!)
            patch_kwargs = {
                "body": resource_dict,
                "name": name,
                "dry_run": dry_run_param,
                "content_type": "application/apply-patch+yaml",
                "field_manager": "zenml",
            }
            if is_namespaced:
                patch_kwargs["namespace"] = namespace

            result = api_resource.patch(**patch_kwargs)

            if not dry_run:
                logger.info(f"{kind} {name} updated successfully")

            return result

        except ApiException as e:
            if e.status == 404:
                # Doesn't exist - create it
                location = (
                    f"in {namespace}" if is_namespaced else "(cluster-scoped)"
                )
                logger.info(
                    f"{'[DRY-RUN] ' if dry_run else ''}Creating {kind} {name} {location}"
                )

                create_kwargs = {
                    "body": resource_dict,
                    "dry_run": dry_run_param,
                }
                if is_namespaced:
                    create_kwargs["namespace"] = namespace

                result = api_resource.create(**create_kwargs)

                if not dry_run:
                    logger.info(f"{kind} {name} created successfully")

                return result
            else:
                # Other error - re-raise
                raise

    def apply_resource(
        self,
        resource: Any,
        dry_run: bool = False,
    ) -> Any:
        """Apply a Kubernetes resource object.

        This method converts a K8s Python object to YAML and then applies it
        using the dynamic client.

        Args:
            resource: Any Kubernetes resource object (V1Deployment, V1Service, etc.).
            dry_run: If True, validate without actually creating/updating.

        Returns:
            The applied resource object.

        Raises:
            ValueError: If resource is invalid.
            ApiException: If the operation fails.
        """
        if hasattr(resource, "to_dict"):
            resource_dict = self.api_client.sanitize_for_serialization(
                resource
            )
        elif isinstance(resource, dict):
            resource_dict = resource
        else:
            raise ValueError(
                f"Resource must be a Kubernetes object or dict, got {type(resource)}"
            )

        if not isinstance(resource_dict, dict):
            raise ValueError(
                f"Serialized resource must be a dict, got {type(resource_dict)}"
            )

        normalized_dict: Dict[str, Any] = dict(resource_dict)

        api_version = normalized_dict.get("apiVersion") or normalized_dict.get(
            "api_version"
        )
        if not api_version and hasattr(resource, "api_version"):
            api_version = getattr(resource, "api_version")

        kind_value = normalized_dict.get("kind")
        if not kind_value and hasattr(resource, "kind"):
            kind_value = getattr(resource, "kind")

        if api_version:
            normalized_dict["apiVersion"] = str(api_version)
        normalized_dict.pop("api_version", None)

        if kind_value:
            normalized_dict["kind"] = str(kind_value)

        if not normalized_dict.get("apiVersion") or not normalized_dict.get(
            "kind"
        ):
            raise ValueError(
                "Resource must have 'kind' and 'apiVersion' fields. "
                f"Got: kind={normalized_dict.get('kind')}, apiVersion={normalized_dict.get('apiVersion')}"
            )

        yaml_content = yaml.dump(
            normalized_dict,
            default_flow_style=False,
        )

        return self.apply_yaml(yaml_content=yaml_content, dry_run=dry_run)

    def delete_resource(
        self,
        name: str,
        namespace: str,
        kind: str,
        api_version: str,
    ) -> None:
        """Delete a Kubernetes resource.

        Args:
            name: Resource name.
            namespace: Kubernetes namespace (ignored for cluster-scoped resources).
            kind: Resource kind (e.g., "Deployment", "Service").
            api_version: API version (e.g., "apps/v1", "v1").

        Raises:
            ValueError: If resource kind is not found.
            ApiException: If the operation fails (except 404).
        """
        try:
            # Get the API resource for this kind
            api_resource = self.dynamic_client.resources.get(
                api_version=api_version,
                kind=kind,
            )
        except ResourceNotFoundError as e:
            raise ValueError(
                f"Unknown resource type: {kind} (apiVersion: {api_version})"
            ) from e

        # Check if this resource is namespaced or cluster-scoped
        is_namespaced = api_resource.namespaced

        # Only use namespace for namespaced resources
        delete_kwargs = {"name": name}
        if is_namespaced:
            delete_kwargs["namespace"] = namespace

        try:
            api_resource.delete(**delete_kwargs)
            logger.info(f"{kind} {name} deleted successfully")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"{kind} {name} not found (already deleted)")
            else:
                raise

    def delete_from_yaml(
        self,
        yaml_content: str,
    ) -> None:
        """Delete a resource defined in YAML.

        Args:
            yaml_content: YAML string containing the resource definition.

        Raises:
            ValueError: If YAML is invalid.
            ApiException: If the operation fails (except 404).
        """
        # Parse YAML
        try:
            resource_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        kind = resource_dict.get("kind")
        api_version = resource_dict.get("apiVersion")
        metadata = resource_dict.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace", "default")

        if not all([kind, api_version, name]):
            raise ValueError(
                "YAML must contain kind, apiVersion, and metadata.name"
            )

        self.delete_resource(
            name=name,
            namespace=namespace,
            kind=kind,
            api_version=api_version,
        )

    # ========================================================================
    # Generic Get/List Methods
    # ========================================================================

    def get_resource(
        self,
        name: str,
        namespace: str,
        kind: str,
        api_version: str,
    ) -> Optional[Any]:
        """Get a Kubernetes resource.

        Args:
            name: Resource name.
            namespace: Kubernetes namespace (ignored for cluster-scoped resources).
            kind: Resource kind (e.g., "Deployment", "Service").
            api_version: API version (e.g., "apps/v1", "v1").

        Returns:
            The resource object, or None if not found.

        Raises:
            ValueError: If resource kind is not found.
            ApiException: If the operation fails (except 404).
        """
        try:
            # Get the API resource for this kind
            api_resource = self.dynamic_client.resources.get(
                api_version=api_version,
                kind=kind,
            )
        except ResourceNotFoundError as e:
            raise ValueError(
                f"Unknown resource type: {kind} (apiVersion: {api_version})"
            ) from e

        # Check if this resource is namespaced or cluster-scoped
        is_namespaced = api_resource.namespaced

        # Only use namespace for namespaced resources
        get_kwargs = {"name": name}
        if is_namespaced:
            get_kwargs["namespace"] = namespace

        try:
            return api_resource.get(**get_kwargs)
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def list_resources(
        self,
        namespace: str,
        kind: str,
        api_version: str,
        label_selector: Optional[str] = None,
    ) -> List[Any]:
        """List Kubernetes resources.

        Args:
            namespace: Kubernetes namespace (ignored for cluster-scoped resources).
            kind: Resource kind (e.g., "Deployment", "Pod").
            api_version: API version (e.g., "apps/v1", "v1").
            label_selector: Optional label selector (e.g., "app=my-app").

        Returns:
            List of resource objects.

        Raises:
            ValueError: If resource kind is not found.
            ApiException: If the operation fails.
        """
        try:
            # Get the API resource for this kind
            api_resource = self.dynamic_client.resources.get(
                api_version=api_version,
                kind=kind,
            )
        except ResourceNotFoundError as e:
            raise ValueError(
                f"Unknown resource type: {kind} (apiVersion: {api_version})"
            ) from e

        # Check if this resource is namespaced or cluster-scoped
        is_namespaced = api_resource.namespaced

        # Build kwargs for get/list operation
        get_kwargs = (
            {"label_selector": label_selector} if label_selector else {}
        )
        if is_namespaced:
            get_kwargs["namespace"] = namespace

        result = api_resource.get(**get_kwargs)
        return result.items if hasattr(result, "items") else []

    # ========================================================================
    # Generic Wait Methods
    # ========================================================================

    def wait_for_resource_condition(
        self,
        name: str,
        namespace: str,
        kind: str,
        api_version: str,
        condition_fn: Callable[[Any], bool],
        timeout: int = 300,
        check_interval: int = 5,
        resource_description: str = "resource",
    ) -> Any:
        """Wait for a resource to meet a condition.

        Args:
            name: Resource name.
            namespace: Kubernetes namespace.
            kind: Resource kind (e.g., "Deployment", "Service").
            api_version: API version (e.g., "apps/v1", "v1").
            condition_fn: Function that takes the resource and returns True when ready.
            timeout: Maximum time to wait in seconds.
            check_interval: Time between checks in seconds.
            resource_description: Human-readable description for logging.

        Returns:
            The resource object when condition is met.

        Raises:
            RuntimeError: If timeout is reached.
            ValueError: If resource kind is not found.
            ApiException: If the operation fails.
        """
        logger.info(
            f"Waiting for {resource_description} '{name}' in namespace '{namespace}' "
            f"(timeout: {timeout}s, check interval: {check_interval}s)"
        )

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                resource = self.get_resource(
                    name=name,
                    namespace=namespace,
                    kind=kind,
                    api_version=api_version,
                )

                if resource is None:
                    logger.warning(
                        f"{resource_description} '{name}' not found, waiting..."
                    )
                elif condition_fn(resource):
                    elapsed = time.time() - start_time
                    logger.info(
                        f"{resource_description} '{name}' ready after {elapsed:.1f}s"
                    )
                    return resource
                else:
                    # Log status for debugging (avoid spam)
                    current_status = str(
                        getattr(resource, "status", "unknown")
                    )
                    if current_status != last_status:
                        logger.info(
                            f"{resource_description} '{name}' not ready yet, waiting..."
                        )
                        last_status = current_status

            except ApiException as e:
                if e.status != 404:
                    raise

            time.sleep(check_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        raise RuntimeError(
            f"{resource_description} '{name}' did not become ready within {elapsed:.1f}s"
        )

    def wait_for_deployment_ready(
        self,
        name: str,
        namespace: str,
        timeout: int = 300,
        check_interval: int = 5,
    ) -> Any:
        """Wait for a Deployment to become ready.

        Args:
            name: Deployment name.
            namespace: Kubernetes namespace.
            timeout: Maximum time to wait in seconds.
            check_interval: Time between checks in seconds.

        Returns:
            The Deployment object when ready.

        Raises:
            RuntimeError: If timeout is reached.
        """

        def deployment_ready(deployment: Any) -> bool:
            """Check if deployment is ready."""
            if not hasattr(deployment, "status") or not deployment.status:
                return False

            status = deployment.status
            desired = getattr(deployment.spec, "replicas", 0)
            available = getattr(status, "available_replicas", 0)

            return available == desired and desired > 0

        return self.wait_for_resource_condition(
            name=name,
            namespace=namespace,
            kind="Deployment",
            api_version="apps/v1",
            condition_fn=deployment_ready,
            timeout=timeout,
            check_interval=check_interval,
            resource_description="Deployment",
        )

    def wait_for_service_loadbalancer_ip(
        self,
        name: str,
        namespace: str,
        timeout: int = 300,
        check_interval: int = 5,
    ) -> str:
        """Wait for a LoadBalancer Service to get an external IP.

        Args:
            name: Service name.
            namespace: Kubernetes namespace.
            timeout: Maximum time to wait in seconds.
            check_interval: Time between checks in seconds.

        Returns:
            The external IP or hostname.

        Raises:
            RuntimeError: If timeout is reached or service is not LoadBalancer type.
        """

        def service_has_loadbalancer_ip(service: Any) -> bool:
            """Check if service has LoadBalancer IP."""
            if not hasattr(service, "status") or not service.status:
                return False

            if not hasattr(service.status, "load_balancer"):
                return False

            load_balancer = service.status.load_balancer
            if (
                not hasattr(load_balancer, "ingress")
                or not load_balancer.ingress
            ):
                return False

            # Check if any ingress entry has IP or hostname
            for ingress in load_balancer.ingress:
                if hasattr(ingress, "ip") and ingress.ip:
                    return True
                if hasattr(ingress, "hostname") and ingress.hostname:
                    return True

            return False

        service = self.wait_for_resource_condition(
            name=name,
            namespace=namespace,
            kind="Service",
            api_version="v1",
            condition_fn=service_has_loadbalancer_ip,
            timeout=timeout,
            check_interval=check_interval,
            resource_description="LoadBalancer Service",
        )

        # Extract the IP/hostname
        for ingress in service.status.load_balancer.ingress:
            if hasattr(ingress, "ip") and ingress.ip:
                ip_str: str = str(ingress.ip)
                return ip_str
            if hasattr(ingress, "hostname") and ingress.hostname:
                hostname_str: str = str(ingress.hostname)
                return hostname_str

        raise RuntimeError("Service has ingress but no IP or hostname found")
