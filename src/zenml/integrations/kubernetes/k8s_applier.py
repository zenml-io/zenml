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
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

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
        dry_run: bool,
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
            dry_run: Whether to do a dry-run
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
        if dry_run:
            kwargs["dry_run"] = "All"
        if timeout is not None:
            kwargs["_request_timeout"] = timeout

        return self.dynamic.server_side_apply(resource=api_resource, **kwargs)

    # --------------------------------------------------------------------- #
    # PROVISION (SSA + optional server-side dry-run)
    # --------------------------------------------------------------------- #

    def provision(
        self,
        objs: Iterable[ResourceLike],
        default_namespace: Optional[str],
        *,
        dry_run: bool,
        field_manager: str = "zenml-deployer",
        force: bool = False,
        timeout: Optional[int] = None,
    ) -> List[Any]:
        """Provision (create/update) resources using **Server-Side Apply**.

        This is declarative and CRD-friendly. When `dry_run=True`, the API server
        validates, defaults, and admits the changes but **does not persist** them.

        Args:
            objs: Iterable of resource dicts or client models. Supports 'kind: List'.
            default_namespace: Namespace to use if a namespaced resource lacks metadata.namespace.
            dry_run: If True, send `?dryRun=All` for a server-side validation only.
            field_manager: Field manager identity for SSA ownership tracking.
            force: If True, force ownership on SSA conflicts (override other managers).
            timeout: Optional request timeout (seconds) passed to the Python client.

        Returns:
            A list of Kubernetes API objects returned by the server.

        Raises:
            ValueError: If an input resource is invalid.
            RuntimeError: If provisioning of a resource fails.
            Exception: For unexpected errors during provisioning.
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

        created_namespaces: List[str] = []

        try:
            for raw in sorted_resources:
                kwargs: Dict[str, Any] = {}
                if default_namespace:
                    kwargs["namespace"] = default_namespace

                is_namespace = raw.get("kind") == "Namespace"
                if dry_run and not is_namespace:
                    kwargs["dry_run"] = "All"

                if timeout is not None:
                    kwargs["_request_timeout"] = timeout

                try:
                    created = self._apply_resource(
                        raw,
                        field_manager=field_manager,
                        force=force,
                        dry_run=dry_run and not is_namespace,
                        namespace=kwargs.get("namespace"),
                        timeout=timeout,
                    )

                    if dry_run and is_namespace:
                        ns_name = (raw.get("metadata") or {}).get("name")
                        if ns_name:
                            created_namespaces.append(ns_name)
                            logger.debug(
                                f"Created namespace '{ns_name}' for dry-run validation"
                            )

                    results.append(created)

                except ApiException as e:
                    error_str = str(e.body) if hasattr(e, "body") else str(e)
                    kind = raw.get("kind", "unknown")
                    name = (raw.get("metadata") or {}).get("name", "unknown")

                    if (
                        dry_run
                        and "namespaces" in error_str
                        and "not found" in error_str.lower()
                    ):
                        logger.warning(
                            f"⚠️  Namespace validation failed for {kind}/{name}. "
                            f"The namespace may need to be created before deployment."
                        )
                        results.append(None)
                        continue

                    raise
                except Exception as exc:
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    kind = raw.get("kind", "unknown")
                    name = (raw.get("metadata") or {}).get("name", "unknown")
                    raise RuntimeError(
                        f"Failed to provision {kind}/{name}: {exc}"
                    ) from exc

        finally:
            if dry_run and created_namespaces:
                logger.debug(
                    f"Cleaning up {len(created_namespaces)} namespace(s) created for dry-run"
                )
                for ns_name in created_namespaces:
                    try:
                        core_v1 = k8s_client.CoreV1Api(self.api_client)
                        core_v1.delete_namespace(
                            name=ns_name,
                            grace_period_seconds=0,
                            propagation_policy="Foreground",
                        )
                        logger.debug(f"Deleted namespace '{ns_name}'")
                    except ApiException as e:
                        logger.warning(
                            f"Failed to clean up namespace '{ns_name}': {e}"
                        )

        return [r for r in results if r is not None]

    # --------------------------------------------------------------------- #
    # DELETE (optionally server-side dry-run)
    # --------------------------------------------------------------------- #

    def delete_by_label_selector(
        self,
        label_selector: str,
        namespace: str,
        *,
        dry_run: bool = False,
        propagation_policy: Optional[str] = "Foreground",
        grace_period_seconds: Optional[int] = None,
        kinds: Optional[List[tuple[str, str]]] = None,
    ) -> int:
        """Delete resources in a namespace by label selector.

        This is useful for cleanup where you want to delete all resources
        matching a label without needing to know exactly what was created.

        Args:
            label_selector: Kubernetes label selector (e.g., "app=myapp,env=prod").
            namespace: Namespace to delete from.
            dry_run: If True, send `?dryRun=All` for validation-only delete.
            propagation_policy: 'Foreground', 'Background', or None.
            grace_period_seconds: Optional grace period override.
            kinds: Optional list of (kind, apiVersion) tuples to delete.
                   If None, deletes common resource types.

        Returns:
            Total number of resources deleted.
        """
        if kinds is None:
            kinds = [
                ("Ingress", "networking.k8s.io/v1"),
                ("Service", "v1"),
                ("Deployment", "apps/v1"),
                ("StatefulSet", "apps/v1"),
                ("DaemonSet", "apps/v1"),
                ("Job", "batch/v1"),
                ("CronJob", "batch/v1"),
                ("ConfigMap", "v1"),
                ("Secret", "v1"),
                ("PersistentVolumeClaim", "v1"),
            ]

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
                    kwargs: Dict[str, Any] = {"namespace": namespace}
                    if dry_run:
                        kwargs["dry_run"] = "All"

                    try:
                        res.delete(name=name, body=body, **kwargs)
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
