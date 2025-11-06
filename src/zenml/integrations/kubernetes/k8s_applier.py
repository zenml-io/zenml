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

import logging
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient

logger = logging.getLogger(__name__)

ResourceLike = Union[Dict[str, Any], Any]


def _flatten_items(objs: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """Yield single resources from possibly 'List' wrappers.

    Kubernetes doesn't have a server-side 'List' kind; it's a client-side aggregation.
    This unwraps {'kind': 'List', 'items': [...]} payloads for convenience.

    Args:
        objs: Iterable of resource dicts (already normalized). Supports 'kind: List'.

    Yields:
        Individual resource dicts.
    """
    for o in objs:
        if (
            isinstance(o, dict)
            and o.get("kind") == "List"
            and isinstance(o.get("items"), list)
        ):
            for item in o["items"]:
                yield item
        else:
            yield o


def _to_dict(
    resource: ResourceLike, api_client: k8s_client.ApiClient
) -> Dict[str, Any]:
    """Normalize a Kubernetes resource (dict or client model) to a plain dict.

    Args:
        resource: A manifest dict or a Kubernetes client model (with .to_dict()).
        api_client: ApiClient used to sanitize/serialize models.

    Returns:
        Normalized manifest as a dict with canonical field casing.

    Raises:
        ValueError: If the resource cannot be converted to a dict.
    """
    if isinstance(resource, dict):
        return resource
    if hasattr(resource, "to_dict"):
        d = api_client.sanitize_for_serialization(resource)
        if not isinstance(d, dict):
            raise ValueError(
                f"Expected dict after serialization, got {type(d)}"
            )
        if "api_version" in d and "apiVersion" not in d:
            d["apiVersion"] = d.pop("api_version")
        return d
    raise ValueError(f"Unsupported resource type: {type(resource)}")


class KubernetesApplier:
    """Generic Kubernetes applier with two modes: provision (SSA) and delete.

    - **provision(...)**: Declarative create/update via Server-Side Apply, with optional server-side dry-run.
    - **delete(...)**: Delete resources, with optional server-side dry-run.

    Also includes helper GET/LIST and simple waiters for Deployment and Service readiness.
    """

    def __init__(self, api_client: k8s_client.ApiClient) -> None:
        """Initialize the applier.

        Args:
            api_client: A configured Kubernetes ApiClient (in-cluster or from kubeconfig).
        """
        self.api_client = api_client
        self.dynamic = DynamicClient(api_client)

    def _apply_resource(
        self,
        resource: Dict[str, Any],
        field_manager: str,
        force: bool,
        namespace: Optional[str],
        timeout: Optional[int],
    ) -> Any:
        """Apply a resource using Server-Side Apply via DynamicClient.

        Uses the DynamicClient which automatically handles resource type
        detection and supports Server-Side Apply.

        Args:
            resource: Resource dictionary
            field_manager: Field manager name for SSA
            force: Whether to force conflicts
            namespace: Default namespace if not in resource
            timeout: Request timeout

        Returns:
            The applied Kubernetes resource
        """
        api_version = resource.get("apiVersion", "v1")
        kind = resource.get("kind")

        api_resource = self.dynamic.resources.get(
            api_version=api_version, kind=kind
        )

        metadata = resource.get("metadata", {})
        resource_name = metadata.get("name")
        resource_namespace = metadata.get("namespace") or namespace

        kwargs = {
            "body": resource,
            "name": resource_name,
        }

        if resource_namespace:
            kwargs["namespace"] = resource_namespace

        if field_manager:
            kwargs["field_manager"] = field_manager
        if force:
            kwargs["force_conflicts"] = True
        if timeout is not None:
            kwargs["_request_timeout"] = timeout

        return self.dynamic.server_side_apply(resource=api_resource, **kwargs)

    # --------------------------------------------------------------------- #
    # PROVISION (SSA)
    # --------------------------------------------------------------------- #

    def provision(
        self,
        objs: Iterable[ResourceLike],
        default_namespace: Optional[str],
        *,
        field_manager: str = "zenml-deployer",
        force: bool = False,
        timeout: Optional[int] = None,
    ) -> List[Any]:
        """Provision (create/update) resources using Server-Side Apply.

        This is declarative and CRD-friendly. Resources are applied in order,
        with namespaces created first to ensure dependencies are satisfied.

        Args:
            objs: Iterable of resource dicts or client models. Supports 'kind: List'.
            default_namespace: Namespace to use if a namespaced resource lacks metadata.namespace.
            field_manager: Field manager identity for SSA ownership tracking.
            force: If True, force ownership on SSA conflicts (override other managers).
            timeout: Optional request timeout (seconds) passed to the Python client.

        Returns:
            A list of Kubernetes API objects returned by the server.

        Raises:
            RuntimeError: If provisioning of a resource fails.
            Exception: If the resource cannot be applied.
        """
        results: List[Any] = []

        all_resources = list(
            _flatten_items([_to_dict(o, self.api_client) for o in objs])
        )

        namespaces = [r for r in all_resources if r.get("kind") == "Namespace"]
        other_resources = [
            r for r in all_resources if r.get("kind") != "Namespace"
        ]
        sorted_resources = namespaces + other_resources

        for raw in sorted_resources:
            try:
                created = self._apply_resource(
                    raw,
                    field_manager=field_manager,
                    force=force,
                    namespace=default_namespace,
                    timeout=timeout,
                )
                results.append(created)

            except Exception as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                kind = raw.get("kind", "unknown")
                name = (raw.get("metadata") or {}).get("name", "unknown")
                raise RuntimeError(
                    f"Failed to provision {kind}/{name}: {exc}"
                ) from exc

        return results

    # --------------------------------------------------------------------- #
    # DELETE
    # --------------------------------------------------------------------- #

    def _discover_deletable_resource_types(
        self,
    ) -> List[Tuple[str, str]]:
        """Dynamically discover all namespaced resource types in the cluster.

        This queries the Kubernetes API to find all available resource types,
        filters for namespaced resources, and returns them in deletion order
        (workloads first, then supporting resources).

        Returns:
            List of (kind, apiVersion) tuples in deletion order.
        """
        discovered_kinds: List[Tuple[str, str]] = []

        # Priority order: delete workloads first, then supporting resources
        priority_order = {
            # Workloads (highest priority - delete first)
            "Ingress": 1,
            "Service": 1,
            "Deployment": 2,
            "StatefulSet": 2,
            "DaemonSet": 2,
            "ReplicaSet": 3,
            "Job": 2,
            "CronJob": 2,
            "Pod": 4,
            # Autoscaling and policies
            "HorizontalPodAutoscaler": 5,
            "PodDisruptionBudget": 5,
            "NetworkPolicy": 5,
            # Configuration and storage
            "ConfigMap": 6,
            "Secret": 6,
            "PersistentVolumeClaim": 6,
            # RBAC
            "ServiceAccount": 7,
            "Role": 7,
            "RoleBinding": 7,
            "ClusterRole": 8,
            "ClusterRoleBinding": 8,
        }

        try:
            # Get all API resources using the discovery API
            # This is equivalent to: kubectl api-resources --namespaced=true
            api_groups = self.dynamic.resources.get()

            for resource in api_groups.resources:
                # Skip if not namespaced
                if not resource.namespaced:
                    continue

                # Skip subresources (e.g., pods/log, pods/status)
                if "/" in resource.name:
                    continue

                # Get the kind and API version
                kind = resource.kind
                api_version = (
                    resource.group_version
                    if hasattr(resource, "group_version")
                    else resource.api_version
                )

                # Skip if we can't determine API version
                if not api_version:
                    continue

                discovered_kinds.append((kind, api_version))

            logger.debug(
                f"Discovered {len(discovered_kinds)} deletable resource types"
            )

            # Sort by priority (lower number = delete first), then by name
            def sort_key(item: Tuple[str, str]) -> Tuple[int, str]:
                kind, _ = item
                priority = priority_order.get(
                    kind, 10
                )  # Default to low priority
                return (priority, kind)

            discovered_kinds.sort(key=sort_key)

            return discovered_kinds

        except Exception as e:
            logger.warning(
                f"Failed to dynamically discover resource types: {e}. "
                f"Falling back to predefined list."
            )
            # Fallback to predefined list
            return [
                ("Ingress", "networking.k8s.io/v1"),
                ("Service", "v1"),
                ("Deployment", "apps/v1"),
                ("StatefulSet", "apps/v1"),
                ("DaemonSet", "apps/v1"),
                ("ReplicaSet", "apps/v1"),
                ("Job", "batch/v1"),
                ("CronJob", "batch/v1"),
                ("Pod", "v1"),
                ("HorizontalPodAutoscaler", "autoscaling/v2"),
                ("PodDisruptionBudget", "policy/v1"),
                ("NetworkPolicy", "networking.k8s.io/v1"),
                ("ConfigMap", "v1"),
                ("Secret", "v1"),
                ("PersistentVolumeClaim", "v1"),
                ("ServiceAccount", "v1"),
                ("Role", "rbac.authorization.k8s.io/v1"),
                ("RoleBinding", "rbac.authorization.k8s.io/v1"),
            ]

    def delete_by_label_selector(
        self,
        label_selector: str,
        namespace: str,
        *,
        propagation_policy: Optional[str] = "Foreground",
        grace_period_seconds: Optional[int] = None,
        kinds: Optional[List[Tuple[str, str]]] = None,
        dynamic_discovery: bool = False,
    ) -> int:
        """Delete resources in a namespace by label selector.

        This is useful for cleanup where you want to delete all resources
        matching a label without needing to know exactly what was created.

        Args:
            label_selector: Kubernetes label selector (e.g., "app=myapp,env=prod").
            namespace: Namespace to delete from.
            propagation_policy: 'Foreground', 'Background', or None.
            grace_period_seconds: Optional grace period override.
            kinds: Optional list of (kind, apiVersion) tuples to delete.
                   If None and dynamic_discovery=False, uses a predefined list.
                   If None and dynamic_discovery=True, discovers all resource types.
            dynamic_discovery: If True, dynamically discover all namespaced resource
                   types in the cluster and check each for the label selector.
                   This is more thorough but slower (10-30s vs 1-3s).

        Returns:
            Total number of resources deleted.
        """
        if kinds is None:
            if dynamic_discovery:
                kinds = self._discover_deletable_resource_types()
            else:
                # Common resource types to delete, ordered by dependency
                # (delete workloads first, then supporting resources)
                kinds = [
                    # Workloads
                    ("Ingress", "networking.k8s.io/v1"),
                    ("Service", "v1"),
                    ("Deployment", "apps/v1"),
                    ("StatefulSet", "apps/v1"),
                    ("DaemonSet", "apps/v1"),
                    ("ReplicaSet", "apps/v1"),
                    ("Job", "batch/v1"),
                    ("CronJob", "batch/v1"),
                    ("Pod", "v1"),
                    # Autoscaling and policies
                    ("HorizontalPodAutoscaler", "autoscaling/v2"),
                    ("PodDisruptionBudget", "policy/v1"),
                    ("NetworkPolicy", "networking.k8s.io/v1"),
                    # Configuration and storage
                    ("ConfigMap", "v1"),
                    ("Secret", "v1"),
                    ("PersistentVolumeClaim", "v1"),
                    # Service accounts and RBAC (if deployment created them)
                    ("ServiceAccount", "v1"),
                    ("Role", "rbac.authorization.k8s.io/v1"),
                    ("RoleBinding", "rbac.authorization.k8s.io/v1"),
                ]
                # Note: Custom resources and CRDs may not be in this list.
                # Use dynamic_discovery=True for comprehensive cleanup.

        total_deleted = 0
        body = k8s_client.V1DeleteOptions()
        if propagation_policy:
            body.propagation_policy = propagation_policy
        if grace_period_seconds is not None:
            body.grace_period_seconds = grace_period_seconds

        for kind, api_version in kinds:
            try:
                res = self.dynamic.resources.get(
                    api_version=api_version, kind=kind
                )

                items = res.get(
                    namespace=namespace,
                    label_selector=label_selector,
                )

                resources_list = items.items if hasattr(items, "items") else []
                if not resources_list:
                    continue

                for item in resources_list:
                    name = item.metadata.name
                    try:
                        res.delete(name=name, body=body, namespace=namespace)
                        total_deleted += 1
                        logger.debug(f"Deleted {kind}/{name} in {namespace}")
                    except ApiException as e:
                        if e.status == 404:
                            continue
                        raise

            except ApiException as e:
                if e.status == 404:
                    logger.debug(
                        f"Resource type {kind} ({api_version}) not found, skipping"
                    )
                    continue
                logger.warning(
                    f"Failed to delete {kind} resources: {e.reason}"
                )

        return total_deleted

    # --------------------------------------------------------------------- #
    # GET / LIST
    # --------------------------------------------------------------------- #

    def get_resource(
        self,
        name: str,
        namespace: Optional[str],
        kind: str,
        api_version: str,
    ) -> Optional[Any]:
        """Fetch a single resource or return None if not found.

        Args:
            name: Resource name.
            namespace: Namespace (ignored for cluster-scoped kinds).
            kind: Kinds like 'Deployment', 'Service', etc.
            api_version: API version string, e.g., 'apps/v1'.

        Returns:
            The resource object if found, None otherwise.

        Raises:
            ApiException: On API errors.
        """
        res = self.dynamic.resources.get(api_version=api_version, kind=kind)
        kwargs: Dict[str, Any] = {"name": name}
        if namespace and res.namespaced:
            kwargs["namespace"] = namespace
        try:
            return res.get(**kwargs)
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def list_resources(
        self,
        kind: str,
        api_version: str,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Any]:
        """List resources of a given kind/apiVersion (optionally by namespace/labels).

        Args:
            kind: Kinds like 'Deployment', 'Service', etc.
            api_version: API version string, e.g., 'apps/v1'.
            namespace: Namespace (ignored for cluster-scoped kinds).
            label_selector: Optional label selector to filter resources.

        Returns:
            A list of resources.
        """
        res = self.dynamic.resources.get(api_version=api_version, kind=kind)
        kwargs: Dict[str, Any] = {}
        if namespace and res.namespaced:
            kwargs["namespace"] = namespace
        if label_selector:
            kwargs["label_selector"] = label_selector
        out = res.get(**kwargs)
        return out.items if hasattr(out, "items") else []

    # --------------------------------------------------------------------- #
    # WAITERS
    # --------------------------------------------------------------------- #

    def wait_for_resource_condition(
        self,
        name: str,
        namespace: Optional[str],
        kind: str,
        api_version: str,
        condition_fn: Callable[[Any], bool],
        timeout: int = 300,
        check_interval: int = 5,
        desc: str = "resource",
    ) -> Any:
        """Poll the object until `condition_fn(obj)` returns True or timeout.

        Args:
            name: Resource name.
            namespace: Namespace (ignored for cluster-scoped kinds).
            kind: Kinds like 'Deployment', 'Service', etc.
            api_version: API version string, e.g., 'apps/v1'.
            condition_fn: Callable that returns True when the resource is ready.
            timeout: Max seconds to wait.
            check_interval: Seconds between polls.
            desc: Human-friendly description for error messages.

        Returns:
            The object that satisfied the condition.

        Raises:
            RuntimeError: If the timeout is reached.
        """
        start = time.time()
        while time.time() - start < timeout:
            obj = self.get_resource(name, namespace, kind, api_version)
            if obj and condition_fn(obj):
                return obj
            time.sleep(check_interval)
        raise RuntimeError(f"{desc} '{name}' not ready within {timeout}s")

    def wait_for_deployment_ready(
        self,
        name: str,
        namespace: str,
        *,
        timeout: int = 300,
        check_interval: int = 5,
    ) -> Any:
        """Wait for a Deployment (apps/v1) to report Available=True.

        Args:
            name: Resource name.
            namespace: Namespace (ignored for cluster-scoped kinds).
            timeout: Max seconds to wait.
            check_interval: Seconds between polls.

        Returns:
            The resource object if found, None otherwise.
        """

        def _ready(dep: Any) -> bool:
            d = dep.to_dict() if hasattr(dep, "to_dict") else dep
            for c in (d.get("status") or {}).get("conditions") or []:
                if c.get("type") == "Available" and c.get("status") == "True":
                    return True
            return False

        return self.wait_for_resource_condition(
            name,
            namespace,
            "Deployment",
            "apps/v1",
            _ready,
            timeout,
            check_interval,
            "Deployment",
        )

    def wait_for_service_loadbalancer_ip(
        self,
        name: str,
        namespace: str,
        *,
        timeout: int = 300,
        check_interval: int = 5,
    ) -> str:
        """Wait for a LoadBalancer Service to publish an external IP/hostname.

        Args:
            name: Service name.
            namespace: Kubernetes namespace.
            timeout: Maximum time to wait in seconds.
            check_interval: Time between checks in seconds.

        Returns:
            The external IP or hostname of the LoadBalancer.

        Raises:
            RuntimeError: If timeout is reached or service has no external IP.
        """
        svc = self.wait_for_resource_condition(
            name,
            namespace,
            "Service",
            "v1",
            lambda s: self._svc_lb_host(s) is not None,
            timeout,
            check_interval,
            "Service",
        )
        host = self._svc_lb_host(svc)
        if not host:
            raise RuntimeError(
                "Service is ready but no external IP/hostname found"
            )
        return host

    def _svc_lb_host(self, service_obj: Any) -> Optional[str]:
        """Extract LoadBalancer IP/hostname if present.

        Args:
            service_obj: Service object.

        Returns:
            LoadBalancer IP/hostname if present.
        """
        s = (
            service_obj.to_dict()
            if hasattr(service_obj, "to_dict")
            else service_obj
        )
        lb = (s.get("status") or {}).get("loadBalancer") or {}
        ingress = lb.get("ingress") or []
        if not ingress:
            return None
        first_ingress = ingress[0]
        ip: Optional[str] = first_ingress.get("ip")
        hostname: Optional[str] = first_ingress.get("hostname")
        return ip or hostname
