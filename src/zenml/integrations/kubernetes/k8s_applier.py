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
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient
from pydantic import BaseModel

from zenml.integrations.kubernetes.serialization_utils import (
    normalize_resource_to_dict,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

ResourceLike = Union[Dict[str, Any], Any]


class ResourceInventoryItem(BaseModel):
    """A single resource in the inventory."""

    api_version: str
    kind: str
    namespace: Optional[str]
    name: str


class DeletionResult(BaseModel):
    """Result of deleting resources from inventory."""

    deleted_count: int
    skipped_count: int
    failed_count: int
    deleted_resources: List[str]
    skipped_resources: List[str]
    failed_resources: List[str]


class ProvisioningError(RuntimeError):
    """Exception raised when resource provisioning fails.

    This exception carries partial results (inventory and errors) to enable
    proper error handling and rollback without losing track of what was created.
    """

    def __init__(
        self,
        message: str,
        inventory: List[ResourceInventoryItem],
        errors: List[str],
    ) -> None:
        """Initialize provisioning error.

        Args:
            message: High-level error message.
            inventory: List of resources successfully provisioned before failure.
            errors: List of error messages for failed resources.
        """
        super().__init__(message)
        self.inventory = inventory
        self.errors = errors


def _flatten_items(objs: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """Yield individual Kubernetes resources, unwrapping any `kind: List` objects.

    Kubernetes allows manifests that wrap multiple resources in a single object:

        kind: List
        items:
          - kind: Deployment
            ...
          - kind: Service
            ...

    Args:
        objs: Iterable of pre-normalized resource dicts

    Yields:
        Individual resource dicts
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


class KubernetesApplier:
    """Kubernetes applier using Server-Side Apply with inventory-based deletion."""

    def __init__(self, api_client: k8s_client.ApiClient) -> None:
        """Initialize the applier.

        Args:
            api_client: A configured Kubernetes ApiClient.
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

        Args:
            resource: Resource dictionary
            field_manager: Field manager name for SSA
            force: Whether to force conflicts (override other field managers)
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
            "content_type": "application/apply-patch+yaml",
        }
        if api_resource.namespaced and resource_namespace:
            kwargs["namespace"] = resource_namespace

        if field_manager:
            kwargs["field_manager"] = field_manager
        if force:
            kwargs["force"] = True
        if timeout is not None:
            kwargs["_request_timeout"] = timeout

        return api_resource.patch(**kwargs)

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
        stop_on_error: bool = True,
    ) -> Tuple[List[Any], List[ResourceInventoryItem]]:
        """Provision (create/update) resources using Server-Side Apply.

        Args:
            objs: Iterable of resource dicts or client models. Supports 'kind: List'.
            default_namespace: Namespace to use if a namespaced resource lacks metadata.namespace.
            field_manager: Field manager identity for SSA ownership tracking.
            force: If True, force ownership on SSA conflicts (override other managers).
            timeout: Optional request timeout (seconds) passed to the Python client.
            stop_on_error: If True, stop provisioning on first error. If False, continue
                with remaining resources and collect all errors.

        Returns:
            A tuple of:
            - List of Kubernetes API objects returned by the server
            - List of inventory items tracking what was created

        Raises:
            ProvisioningError: If provisioning fails, with partial inventory and error details.
            Exception: If provisioning fails for KeyboardInterrupt or SystemExit.
        """
        results: List[Any] = []
        inventory: List[ResourceInventoryItem] = []
        errors: List[str] = []

        all_resources = list(
            _flatten_items([normalize_resource_to_dict(obj) for obj in objs])
        )

        namespaces = [
            resource
            for resource in all_resources
            if resource.get("kind") == "Namespace"
        ]
        other_resources = [
            resource
            for resource in all_resources
            if resource.get("kind") != "Namespace"
        ]
        sorted_resources = namespaces + other_resources

        for raw in sorted_resources:
            kind = raw.get("kind", "unknown")
            name = (raw.get("metadata") or {}).get("name", "unknown")

            try:
                created = self._apply_resource(
                    raw,
                    field_manager=field_manager,
                    force=force,
                    namespace=default_namespace,
                    timeout=timeout,
                )
                results.append(created)

                api_version = raw.get("apiVersion", "v1")
                api_resource = self.dynamic.resources.get(
                    api_version=api_version, kind=kind
                )
                metadata = raw.get("metadata", {})

                item_namespace = None
                if api_resource.namespaced:
                    item_namespace = (
                        metadata.get("namespace") or default_namespace
                    )

                inventory.append(
                    ResourceInventoryItem(
                        api_version=api_version,
                        kind=kind,
                        namespace=item_namespace,
                        name=name,
                    )
                )
                logger.debug(f"Applied {kind}/{name}")

            except Exception as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise

                error_msg = f"Failed to provision {kind}/{name}: {exc}"
                errors.append(error_msg)

                if stop_on_error:
                    raise ProvisioningError(
                        f"Failed while provisioning {kind}/{name}",
                        inventory=inventory,
                        errors=errors,
                    ) from exc
                else:
                    continue

        if errors:
            raise ProvisioningError(
                f"Provisioning completed with {len(errors)} error(s)",
                inventory=inventory,
                errors=errors,
            )

        return results, inventory

    # --------------------------------------------------------------------- #
    # DELETE
    # --------------------------------------------------------------------- #

    def delete_from_inventory(
        self,
        inventory: List[ResourceInventoryItem],
        *,
        propagation_policy: Optional[str] = "Foreground",
        grace_period_seconds: Optional[int] = None,
    ) -> DeletionResult:
        """Delete resources from an inventory list (Helm/Flux/Argo pattern).

        Args:
            inventory: List of resources to delete (from provision() return value).
            propagation_policy: 'Foreground', 'Background', or None.
            grace_period_seconds: Optional grace period override.

        Returns:
            DeletionResult containing counts and lists of deleted, skipped, and failed resources.
        """
        deleted_resources: List[str] = []
        skipped_resources: List[str] = []
        failed_resources: List[str] = []

        body = k8s_client.V1DeleteOptions()
        if propagation_policy:
            body.propagation_policy = propagation_policy
        if grace_period_seconds is not None:
            body.grace_period_seconds = grace_period_seconds

        for item in reversed(inventory):
            resource_desc = (
                f"{item.kind}/{item.name} "
                f"(apiVersion: {item.api_version}, "
                f"namespace: {item.namespace or 'cluster-scoped'})"
            )

            if item.kind == "Namespace":
                logger.info(
                    f"⏩ Skipping namespace '{item.name}' "
                    f"(namespaces are never deleted to prevent accidental "
                    f"cascade deletion of shared resources)"
                )
                skipped_resources.append(resource_desc)
                continue

            try:
                res = self.dynamic.resources.get(
                    api_version=item.api_version, kind=item.kind
                )

                kwargs: Dict[str, Any] = {"name": item.name, "body": body}
                if item.namespace and res.namespaced:
                    kwargs["namespace"] = item.namespace

                res.delete(**kwargs)
                deleted_resources.append(resource_desc)
            except ApiException as e:
                if e.status == 404:
                    skipped_resources.append(resource_desc)
                    continue
                error_msg = f"{resource_desc}: {e.reason}"
                failed_resources.append(error_msg)
                logger.error(f"❌ Failed to delete {error_msg}")
            except Exception as e:
                error_msg = f"{resource_desc}: {str(e)}"
                failed_resources.append(error_msg)
                logger.error(f"❌ Failed to delete {error_msg}")

        if failed_resources:
            logger.warning(
                f"Failed to delete {len(failed_resources)}/{len(inventory)} resource(s)"
            )

        return DeletionResult(
            deleted_count=len(deleted_resources),
            skipped_count=len(skipped_resources),
            failed_count=len(failed_resources),
            deleted_resources=deleted_resources,
            skipped_resources=skipped_resources,
            failed_resources=failed_resources,
        )

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
            kind: Resource kind (e.g., 'Deployment', 'Service', 'Pod')
            api_version: API version string (e.g., 'apps/v1', 'v1')
            namespace: Namespace for namespaced resources (ignored for cluster-scoped)
            label_selector: Optional label selector to filter resources
                (e.g., 'app=myapp,env=prod')

        Returns:
            List of resource objects matching the query criteria.
            Returns empty list only if the API explicitly returns zero items.

        Raises:
            TypeError: If the API response is malformed (missing .items attribute
                or .items is not a list). This indicates a serious API or client issue.
        """
        res = self.dynamic.resources.get(api_version=api_version, kind=kind)
        kwargs: Dict[str, Any] = {}
        if namespace and res.namespaced:
            kwargs["namespace"] = namespace
        if label_selector:
            kwargs["label_selector"] = label_selector
        out = res.get(**kwargs)

        try:
            items = out.items
        except AttributeError:
            logger.error(
                f"API response for {kind} list has no .items attribute. "
                f"Response type: {type(out).__name__}. "
                f"This indicates a serious issue with the Kubernetes API or client."
            )
            raise TypeError(
                f"Malformed API response for {kind} list: missing .items attribute. "
                f"Response type: {type(out).__name__}"
            )

        if not isinstance(items, list):
            logger.error(
                f"API response for {kind} list has non-list .items: {type(items).__name__}. "
                f"This indicates a serious issue with the Kubernetes API or client."
            )
            raise TypeError(
                f"Malformed API response for {kind} list: .items is not a list. "
                f"Got {type(items).__name__} instead."
            )

        return items

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
            The raw resource object from the dynamic client.

        Note:
            Internally normalizes the deployment to a dict for inspection,
            but returns the original object from the API.
        """

        def _ready(deployment: Any) -> bool:
            deployment_dict = normalize_resource_to_dict(deployment)
            metadata = deployment_dict.get("metadata") or {}
            status = deployment_dict.get("status") or {}
            observed_generation = status.get("observedGeneration")
            generation = metadata.get("generation")

            if (
                generation
                and observed_generation
                and observed_generation < generation
            ):
                return False

            conditions = {
                condition.get("type"): condition
                for condition in (status.get("conditions") or [])
            }

            available = conditions.get("Available", {})
            progressing = conditions.get("Progressing", {})

            if available.get("status") != "True":
                return False

            if progressing.get("status") == "False":
                reason = progressing.get("reason", "")
                if reason == "ProgressDeadlineExceeded":
                    raise RuntimeError(
                        f"Deployment rollout stuck: {progressing.get('message', 'Unknown')}"
                    )
                return False

            replicas = status.get("replicas", 0)
            updated_replicas = status.get("updatedReplicas", 0)
            available_replicas = status.get("availableReplicas", 0)

            if replicas == 0:
                return True

            return bool(
                updated_replicas == replicas and available_replicas == replicas
            )

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
            service_obj: Service object from dynamic client.

        Returns:
            LoadBalancer IP/hostname if present, None otherwise.
        """
        service_dict = normalize_resource_to_dict(service_obj)
        lb = (service_dict.get("status") or {}).get("loadBalancer") or {}
        ingress = lb.get("ingress") or []
        if not ingress:
            return None
        first_ingress = ingress[0]
        ip: Optional[str] = first_ingress.get("ip")
        hostname: Optional[str] = first_ingress.get("hostname")
        return ip or hostname
