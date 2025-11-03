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
#  OR implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Kubernetes resource applier."""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from kubernetes import client as k8s_client
from kubernetes import dynamic
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.exceptions import ResourceNotFoundError

from zenml.integrations.kubernetes.kube_utils import (
    build_url_from_loadbalancer_service,
    retry_on_api_exception,
)
from zenml.logger import get_logger
from zenml.utils.yaml_utils import load_yaml_documents

logger = get_logger(__name__)


class KubernetesApplier:
    """Kubernetes resource applier.

    This class uses the Kubernetes Dynamic Client to apply ANY resource type
    WITHOUT needing hardcoded mappings! The K8s API server tells us everything
    we need to know about each resource type through API discovery.

    Example:
        applier = KubernetesApplier(api_client=k8s_client.ApiClient())

        # Apply YAML directly - no need to know the type!
        applier.apply_yaml(yaml_string, namespace="default")

        # Or apply a K8s object
        applier.apply_resource(k8s_deployment)

        # Delete by name/namespace/kind
        applier.delete_resource("my-app", "default", "Deployment", "apps/v1")

    How it works:
    1. Parses YAML to extract kind and apiVersion
    2. Uses dynamic client to discover the resource API
    3. Automatically handles create-or-update logic via Server-Side Apply (SSA)
    4. Works for ANY K8s resource - built-in or CRDs!
    """

    def __init__(self, api_client: k8s_client.ApiClient):
        """Initialize the applier with a Kubernetes API client.

        Args:
            api_client: Kubernetes API client (can be from connector or kubeconfig).
        """
        self.api_client = api_client
        self.dynamic_client = dynamic.DynamicClient(api_client)
        self._resource_cache: Dict[Tuple[str, str], Any] = {}

    def _get_api_resource(
        self, api_version: str, kind: str, retries: int = 3
    ) -> dynamic.Resource:
        """Get API resource with caching and retry logic.

        Args:
            api_version: API version (e.g., "apps/v1").
            kind: Resource kind (e.g., "Deployment").
            retries: Number of times to retry discovery on transient failures.

        Returns:
            Dynamic API resource object.

        Raises:
            ValueError: If resource type is unknown.
        """
        cache_key = (api_version, kind)
        if cache_key not in self._resource_cache:
            try:
                get_resource_fn = retry_on_api_exception(
                    self.dynamic_client.resources.get,
                    max_retries=retries,
                    delay=1.0,
                    backoff=2.0,
                )
                self._resource_cache[cache_key] = get_resource_fn(
                    api_version=api_version,
                    kind=kind,
                )
            except ResourceNotFoundError as e:
                raise ValueError(
                    f"Unknown resource type: {kind} (apiVersion: {api_version})"
                ) from e
        return self._resource_cache[cache_key]

    def ssa_apply(
        self,
        resource: Dict[str, Any],
        *,
        namespace: Optional[str] = None,
        field_manager: str = "zenml",
        dry_run: bool = False,
        force: bool = False,
    ) -> Any:
        """Apply a resource using Server-Side Apply (SSA).

        SSA is the modern, recommended way to apply Kubernetes resources.
        It provides better conflict resolution and field ownership tracking.

        Args:
            resource: Resource dict with apiVersion, kind, and metadata.
            namespace: Namespace for namespaced resources. If the resource is
                namespaced and this is None, the namespace from metadata.namespace
                will be used. If that's also missing, a ValueError is raised to
                prevent silent defaults.
            field_manager: Name of the field manager (for SSA ownership tracking).
            dry_run: If True, validate without actually creating/updating.
            force: If True, force ownership of conflicting fields.

        Returns:
            The applied resource object.

        Raises:
            ValueError: If resource is invalid or namespace is required but missing.
        """
        kind = resource.get("kind")
        api_version = resource.get("apiVersion")

        if not kind or not api_version:
            raise ValueError(
                "Resource must have 'kind' and 'apiVersion' fields"
            )

        api_resource = self._get_api_resource(api_version, kind)
        is_namespaced = api_resource.namespaced

        effective_namespace = namespace
        if is_namespaced:
            if not effective_namespace:
                effective_namespace = resource.get("metadata", {}).get(
                    "namespace"
                )
            if not effective_namespace:
                raise ValueError(
                    f"Namespaced resource {kind}/{resource.get('metadata', {}).get('name', 'unknown')} "
                    f"requires an explicit namespace parameter or metadata.namespace field"
                )

            # Sync namespace parameter with resource metadata to avoid 422/409 errors
            resource.setdefault("metadata", {})["namespace"] = (
                effective_namespace
            )

        metadata = resource.get("metadata", {})
        name = metadata.get("name")
        if not name:
            raise ValueError("Resource must have 'metadata.name' field")

        kwargs = {
            "body": resource,
            "name": name,
            "content_type": "application/apply-patch+yaml",
            "field_manager": field_manager,
        }

        if is_namespaced:
            kwargs["namespace"] = effective_namespace

        if dry_run:
            kwargs["dry_run"] = "All"

        if force:
            kwargs["force"] = True

        return retry_on_api_exception(
            api_resource.patch,
            max_retries=3,
            delay=1.0,
            backoff=2.0,
        )(**kwargs)

    def apply_yaml(
        self,
        yaml_content: str,
        *,
        namespace: Optional[str] = None,
        field_manager: str = "zenml",
        dry_run: bool = False,
        force: bool = False,
    ) -> List[Any]:
        """Apply Kubernetes resource(s) from YAML string using Server-Side Apply.

        Supports both single-document and multi-document YAML (with --- separators).

        Args:
            yaml_content: YAML string containing one or more resource definitions.
            namespace: Default namespace for namespaced resources that don't
                specify metadata.namespace.
            field_manager: Name of the field manager (for SSA ownership tracking).
            dry_run: If True, validate without actually creating/updating.
            force: If True, force ownership of conflicting fields.

        Returns:
            List of applied resource objects.

        Raises:
            ValueError: If YAML is invalid or missing required fields.
        """
        resources = load_yaml_documents(yaml_content)

        applied_resources = []
        for resource in resources:
            applied = self.ssa_apply(
                resource=resource,
                namespace=namespace,
                field_manager=field_manager,
                dry_run=dry_run,
                force=force,
            )
            applied_resources.append(applied)

        return applied_resources

    def apply_resource(
        self,
        resource: Any,
        *,
        namespace: Optional[str] = None,
        field_manager: str = "zenml",
        dry_run: bool = False,
        force: bool = False,
    ) -> Any:
        """Apply a Kubernetes resource object or dict using Server-Side Apply.

        Args:
            resource: Any Kubernetes resource object (V1Deployment, V1Service, etc.) or dict.
            namespace: Namespace for namespaced resources.
            field_manager: Name of the field manager (for SSA ownership tracking).
            dry_run: If True, validate without actually creating/updating.
            force: If True, force ownership of conflicting fields.

        Returns:
            The applied resource object.

        Raises:
            ValueError: If resource is invalid.
        """
        resource_dict = self._normalize_resource(resource)
        return self.ssa_apply(
            resource=resource_dict,
            namespace=namespace,
            field_manager=field_manager,
            dry_run=dry_run,
            force=force,
        )

    def _normalize_resource(self, resource: Any) -> Dict[str, Any]:
        """Normalize a Kubernetes resource to a dictionary.

        Args:
            resource: Kubernetes resource object or dict.

        Returns:
            Resource as a dictionary with normalized field names.

        Raises:
            ValueError: If resource cannot be normalized.
        """
        if isinstance(resource, dict):
            resource_dict = resource
        elif hasattr(resource, "to_dict"):
            resource_dict = self.api_client.sanitize_for_serialization(
                resource
            )
        else:
            raise ValueError(
                f"Resource must be a Kubernetes object or dict, got {type(resource)}"
            )

        if not isinstance(resource_dict, dict):
            raise ValueError(
                f"Serialized resource must be a dict, got {type(resource_dict)}"
            )

        api_version = resource_dict.get("apiVersion") or resource_dict.get(
            "api_version"
        )
        if not api_version and hasattr(resource, "api_version"):
            api_version = getattr(resource, "api_version")

        kind_value = resource_dict.get("kind")
        if not kind_value and hasattr(resource, "kind"):
            kind_value = getattr(resource, "kind")

        if api_version:
            resource_dict["apiVersion"] = str(api_version)
        resource_dict.pop("api_version", None)

        if kind_value:
            resource_dict["kind"] = str(kind_value)

        if not resource_dict.get("apiVersion") or not resource_dict.get(
            "kind"
        ):
            raise ValueError(
                "Resource must have 'kind' and 'apiVersion' fields. "
                f"Got: kind={resource_dict.get('kind')}, apiVersion={resource_dict.get('apiVersion')}"
            )

        return resource_dict

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
        api_resource = self._get_api_resource(api_version, kind)
        is_namespaced = api_resource.namespaced

        delete_kwargs = {"name": name}
        if is_namespaced:
            delete_kwargs["namespace"] = namespace

        try:
            retry_on_api_exception(
                api_resource.delete,
                max_retries=3,
                delay=1.0,
                backoff=2.0,
            )(**delete_kwargs)
            logger.info(f"{kind} {name} deleted successfully")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"{kind} {name} not found (already deleted)")
            else:
                raise

    def delete_from_yaml(
        self,
        yaml_content: str,
        *,
        namespace: Optional[str] = None,
    ) -> None:
        """Delete resource(s) defined in YAML.

        Supports both single-document and multi-document YAML.

        Args:
            yaml_content: YAML string containing one or more resource definitions.
            namespace: Default namespace for namespaced resources that don't
                specify metadata.namespace.

        Raises:
            ValueError: If YAML is invalid or namespace is required but missing.
        """
        resources = load_yaml_documents(yaml_content)

        for resource in resources:
            kind_raw = resource.get("kind")
            api_version_raw = resource.get("apiVersion")
            metadata = resource.get("metadata", {})
            name_raw = metadata.get("name")

            if not kind_raw or not api_version_raw or not name_raw:
                raise ValueError(
                    "Each YAML document must contain kind, apiVersion, and metadata.name"
                )

            # These are guaranteed to be strings after the check above
            kind = cast(str, kind_raw)
            api_version = cast(str, api_version_raw)
            name = cast(str, name_raw)

            # Determine if resource is namespaced
            try:
                api_resource = self._get_api_resource(api_version, kind)
                is_namespaced = api_resource.namespaced
            except ValueError:
                # Resource type unknown, require explicit namespace
                is_namespaced = True
                logger.warning(
                    f"Cannot determine scope for {kind} (apiVersion={api_version}), "
                    f"assuming namespaced"
                )

            # Resolve namespace for namespaced resources
            effective_namespace = namespace
            if is_namespaced:
                if not effective_namespace:
                    effective_namespace = metadata.get("namespace")
                if not effective_namespace:
                    raise ValueError(
                        f"Namespaced resource {kind}/{name} requires an explicit "
                        f"namespace parameter or metadata.namespace field"
                    )

            self.delete_resource(
                name=name,
                namespace=effective_namespace or "",
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
        """
        api_resource = self._get_api_resource(api_version, kind)
        is_namespaced = api_resource.namespaced

        get_kwargs = {"name": name}
        if is_namespaced:
            get_kwargs["namespace"] = namespace

        try:
            return retry_on_api_exception(api_resource.get)(**get_kwargs)
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
        """
        api_resource = self._get_api_resource(api_version, kind)
        is_namespaced = api_resource.namespaced

        get_kwargs = (
            {"label_selector": label_selector} if label_selector else {}
        )
        if is_namespaced:
            get_kwargs["namespace"] = namespace

        result = retry_on_api_exception(api_resource.get)(**get_kwargs)
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
        """
        logger.info(
            f"Waiting for {resource_description} '{name}' in namespace '{namespace}' "
            f"(timeout: {timeout}s, check interval: {check_interval}s)"
        )

        start_time = time.time()
        last_generation = None
        log_counter = 0

        while time.time() - start_time < timeout:
            try:
                resource = self.get_resource(
                    name=name,
                    namespace=namespace,
                    kind=kind,
                    api_version=api_version,
                )

                if resource is None:
                    logger.debug(
                        f"{resource_description} '{name}' not found, waiting..."
                    )
                elif condition_fn(resource):
                    elapsed = time.time() - start_time
                    logger.info(
                        f"{resource_description} '{name}' ready after {elapsed:.1f}s"
                    )
                    return resource
                else:
                    # Track generation for change detection (lightweight hash)
                    if hasattr(resource, "metadata"):
                        current_generation = getattr(
                            resource.metadata, "generation", None
                        )
                    else:
                        current_generation = None

                    if current_generation != last_generation:
                        logger.debug(
                            f"{resource_description} '{name}' not ready yet, waiting..."
                        )
                        last_generation = current_generation
                    else:
                        # Log periodically even if no change (every 6 polls = 30s at default interval)
                        log_counter += 1
                        if log_counter >= 6:
                            logger.debug(
                                f"{resource_description} '{name}' still waiting..."
                            )
                            log_counter = 0

            except ApiException as e:
                if e.status != 404:
                    raise

            time.sleep(check_interval)

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

        A deployment is considered ready when its Available condition is True.

        Args:
            name: Deployment name.
            namespace: Kubernetes namespace.
            timeout: Maximum time to wait in seconds.
            check_interval: Time between checks in seconds.

        Returns:
            The Deployment object when ready.
        """

        def deployment_ready(deployment: Any) -> bool:
            """Check if deployment is ready by inspecting status.conditions.

            Args:
                deployment: The Deployment object to check.

            Returns:
                True if deployment is ready (Available=True), False otherwise.
            """
            if hasattr(deployment, "to_dict"):
                deployment_dict = deployment.to_dict()
            else:
                deployment_dict = deployment

            status = deployment_dict.get("status", {})
            conditions = status.get("conditions", [])

            for condition in conditions:
                if isinstance(condition, dict):
                    condition_type = condition.get("type")
                    condition_status = condition.get("status")
                else:
                    condition_type = getattr(condition, "type", None)
                    condition_status = getattr(condition, "status", None)

                if (
                    condition_type == "Available"
                    and condition_status == "True"
                ):
                    return True

            spec = deployment_dict.get("spec", {})
            desired = int(spec.get("replicas", 0))
            available = int(status.get("availableReplicas", 0))
            logger.debug(
                f"Deployment {name} not ready: {available}/{desired} replicas available, "
                f"Available condition not True"
            )
            return False

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
            """Check if service has LoadBalancer IP.

            Args:
                service: The Service object to check.

            Returns:
                True if LoadBalancer has an IP assigned, False otherwise.
            """
            url = build_url_from_loadbalancer_service(service)
            return url is not None

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

        url = build_url_from_loadbalancer_service(service)
        if not url:
            raise RuntimeError(
                "Service ready but no LoadBalancer IP/hostname found"
            )

        host = url.split("://")[1].split(":")[0] if "://" in url else url
        return host

    # ========================================================================
    # Resource Namespace Management
    # ========================================================================

    def ensure_namespace_alignment(
        self,
        resource_dict: Dict[str, Any],
        namespace: str,
        deployment_name: str,
        *,
        allow_unknown_resources: bool = True,
    ) -> None:
        """Ensure resource namespace matches its scope.

        Modifies resource_dict in place by:
        - Setting namespace for namespaced resources without one
        - Removing namespace for cluster-scoped resources
        - For unknown resources (e.g., CRDs not yet applied), assumes namespaced
          if allow_unknown_resources=True

        Args:
            resource_dict: The Kubernetes manifest to apply (mutated in place).
            namespace: Target deployment namespace.
            deployment_name: Name of the deployment (for logging context).
            allow_unknown_resources: If True, unknown resource types are assumed
                to be namespaced and the manifest is left as-is. If False, raises
                ValueError for unknown types.

        Raises:
            ValueError: If resource scope cannot be determined and allow_unknown_resources=False.
        """
        metadata = resource_dict.get("metadata") or {}
        resource_name = metadata.get(
            "name", resource_dict.get("kind", "unknown")
        )
        kind = resource_dict.get("kind", "unknown")
        api_version = resource_dict.get("apiVersion", "unknown")

        scope_result = self.is_resource_namespaced(resource_dict)

        if scope_result is None:
            if not allow_unknown_resources:
                raise ValueError(
                    f"Cannot determine scope for additional resource '{resource_name}' "
                    f"(kind={kind}, apiVersion={api_version}) "
                    f"for deployment '{deployment_name}'. The resource type may not exist in the cluster."
                )
            logger.info(
                f"Resource type {kind} (apiVersion={api_version}) not yet discovered "
                f"for deployment '{deployment_name}'. Assuming namespaced and proceeding. "
                f"If this is a CRD, ensure it's applied before dependent resources."
            )
            if not metadata.get("namespace"):
                resource_dict.setdefault("metadata", {})["namespace"] = (
                    namespace
                )
            return

        is_namespaced = scope_result

        if is_namespaced:
            if not metadata.get("namespace"):
                resource_dict.setdefault("metadata", {})["namespace"] = (
                    namespace
                )
        else:
            if metadata.get("namespace"):
                logger.warning(
                    f"Additional resource '{resource_name}' for deployment '{deployment_name}' "
                    f"is cluster-scoped but declares namespace '{metadata['namespace']}'. "
                    f"Removing namespace field to prevent API rejection."
                )
                del metadata["namespace"]

    def is_resource_namespaced(
        self, resource_dict: Dict[str, Any]
    ) -> Optional[bool]:
        """Determine whether a resource is namespaced.

        Args:
            resource_dict: Kubernetes manifest dictionary.

        Returns:
            True if the resource is namespaced, False if cluster-scoped,
            None if the information cannot be determined.

        Raises:
            ValueError: If API discovery fails with an unexpected error.
        """
        api_version = resource_dict.get("apiVersion")
        kind = resource_dict.get("kind")

        if not api_version or not kind:
            return None

        try:
            api_resource = self._get_api_resource(api_version, kind)
            return bool(getattr(api_resource, "namespaced", False))
        except ValueError:
            logger.warning(
                f"Unknown resource kind '{kind}' (apiVersion={api_version}); "
                f"cannot determine namespace scope."
            )
            return None
        except Exception as exc:
            raise ValueError(
                f"Failed to inspect resource kind '{kind}' (apiVersion={api_version}): {exc}"
            ) from exc
