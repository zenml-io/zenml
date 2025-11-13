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

import time
import types

import pytest
from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

# Import module so we can monkeypatch the DynamicClient symbol it uses
from zenml.integrations.kubernetes import k8s_applier as k8s_applier_module
from zenml.integrations.kubernetes.k8s_applier import (
    DeletionResult,
    KubernetesApplier,
    ProvisioningError,
    ResourceInventoryItem,
    _flatten_items,
    _to_dict,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class DummyApiClient(k8s_client.ApiClient):
    """Minimal ApiClient stub for sanitize_for_serialization."""

    def sanitize_for_serialization(self, obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return obj


class DummyModel:
    """Simple model type that mimics Kubernetes client models."""

    def __init__(
        self, api_version="v1", kind="ConfigMap", name="cm", extra=None
    ):
        self.api_version = api_version
        self.kind = kind
        self.metadata = types.SimpleNamespace(name=name)
        self.extra = extra

    def to_dict(self):
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": {"name": self.metadata.name},
        }
        if self.extra is not None:
            data["extra"] = self.extra
        return data


class DummyBadModel:
    """Model whose to_dict() returns a non-dict, to exercise _to_dict error path."""

    def to_dict(self):
        return ["not", "a", "dict"]


class DummyResource:
    """Fake dynamic resource wrapper implementing subset used by KubernetesApplier."""

    def __init__(self, kind: str, api_version: str, namespaced: bool = True):
        self.kind = kind
        self.api_version = api_version
        self.namespaced = namespaced
        self.applied = []  # patch() calls
        self.deleted = []  # delete() calls
        self.list_items = []  # returned by get(..., label_selector=...) or list calls
        self.raise_on_patch = {}  # name -> Exception to raise on patch
        self.raise_on_delete = {}  # name -> Exception to raise on delete

    # Server-side apply / patch
    def patch(self, **kwargs):
        name = kwargs.get("name")
        if name in self.raise_on_patch:
            raise self.raise_on_patch[name]
        self.applied.append(kwargs)

        namespace = kwargs.get("namespace")

        def _to_dict():
            return {
                "apiVersion": self.api_version,
                "kind": self.kind,
                "metadata": {"name": name, "namespace": namespace},
            }

        return types.SimpleNamespace(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata={"name": name, "namespace": namespace},
            to_dict=_to_dict,
        )

    # get() is used both for single get and list-style get
    def get(self, **kwargs):
        # list-style invocation
        if "label_selector" in kwargs or (
            "namespace" in kwargs and "name" not in kwargs
        ):
            return types.SimpleNamespace(items=self.list_items)

        # direct get by name
        name = kwargs.get("name")
        for item in self.list_items:
            if getattr(item.metadata, "name", None) == name:
                return item

        raise ApiException(status=404, reason="Not Found")

    def delete(self, **kwargs):
        name = kwargs["name"]
        if name in self.raise_on_delete:
            raise self.raise_on_delete[name]
        self.deleted.append(kwargs)


class DummyDynamic:
    """In-memory DynamicClient-like registry.

    KubernetesApplier only relies on dynamic.resources.get(api_version=..., kind=...).
    """

    def __init__(self):
        # (api_version, kind) -> DummyResource
        self._registry = {}

    def register(self, api_version: str, kind: str, namespaced: bool = True):
        res = DummyResource(
            kind=kind, api_version=api_version, namespaced=namespaced
        )
        self._registry[(api_version, kind)] = res
        return res

    class _ResourcesView:
        def __init__(self, registry):
            self._registry = registry

        def get(self, api_version: str, kind: str):
            return self._registry[(api_version, kind)]

    @property
    def resources(self):
        return DummyDynamic._ResourcesView(self._registry)


@pytest.fixture
def api_client():
    return DummyApiClient()


@pytest.fixture
def applier(api_client, monkeypatch):
    """KubernetesApplier wired to an in-memory DummyDynamic instead of a real cluster."""
    dyn = DummyDynamic()

    # Pre-register core resource types
    ns_res = dyn.register("v1", "Namespace", namespaced=False)
    cm_res = dyn.register("v1", "ConfigMap", namespaced=True)
    dep_res = dyn.register("apps/v1", "Deployment", namespaced=True)
    svc_res = dyn.register("v1", "Service", namespaced=True)
    pod_res = dyn.register("v1", "Pod", namespaced=True)

    class FakeDynamicClient:
        def __init__(self, _api_client):
            self._dyn = dyn
            self.resources = dyn.resources

    # Patch symbol used inside k8s_applier.py
    monkeypatch.setattr(k8s_applier_module, "DynamicClient", FakeDynamicClient)

    k = KubernetesApplier(api_client=api_client)

    # Expose handles for assertions
    k._test_dyn = dyn
    k._test_ns = ns_res
    k._test_cm = cm_res
    k._test_dep = dep_res
    k._test_svc = svc_res
    k._test_pod = pod_res

    return k


# ---------------------------------------------------------------------------
# Helper function tests: _flatten_items / _to_dict
# ---------------------------------------------------------------------------


def test_flatten_items_expands_kind_list_and_leaves_others():
    objs = [
        {"kind": "ConfigMap", "metadata": {"name": "a"}},
        {
            "kind": "List",
            "items": [
                {"kind": "ConfigMap", "metadata": {"name": "b"}},
                {"kind": "Secret", "metadata": {"name": "c"}},
            ],
        },
        # Not a list because "items" is not a list → should be yielded as-is
        {"kind": "List", "items": "not-a-list", "metadata": {"name": "weird"}},
    ]

    out = list(_flatten_items(objs))
    assert len(out) == 4
    assert {o["metadata"]["name"] for o in out} == {"a", "b", "c", "weird"}


def test_to_dict_with_dict_returns_same_instance(api_client):
    obj = {"apiVersion": "v1", "kind": "ConfigMap"}
    out = _to_dict(obj, api_client)
    assert out is obj


def test_to_dict_with_model_uses_sanitize_and_normalizes_api_version(
    api_client,
):
    model = DummyModel(api_version="v1", kind="ConfigMap", name="cm1")
    out = _to_dict(model, api_client)
    assert out["apiVersion"] == "v1"
    assert out["kind"] == "ConfigMap"
    assert out["metadata"]["name"] == "cm1"


def test_to_dict_with_model_wrapping_api_version_key(api_client):
    """If sanitize_for_serialization returns 'api_version', we normalize to 'apiVersion'."""

    class ModelWithApiVersionAttr:
        def __init__(self):
            self.api_version = "batch/v1"

        def to_dict(self):
            # Won't actually be used because DummyApiClient uses its own to_dict
            return {"api_version": "batch/v1", "metadata": {"name": "job"}}

    # We want DummyApiClient.sanitize_for_serialization to return a dict with api_version
    class ApiClientWithApiVersion(DummyApiClient):
        def sanitize_for_serialization(self, obj):
            return {
                "api_version": "batch/v1",
                "kind": "Job",
                "metadata": {"name": "job"},
            }

    api_client2 = ApiClientWithApiVersion()
    model = ModelWithApiVersionAttr()
    out = _to_dict(model, api_client2)
    assert out["apiVersion"] == "batch/v1"
    assert "api_version" not in out


def test_to_dict_with_model_returning_non_dict_raises(api_client):
    with pytest.raises(ValueError, match="Expected dict after serialization"):
        _to_dict(DummyBadModel(), api_client)


def test_to_dict_with_unsupported_type_raises(api_client):
    with pytest.raises(ValueError, match="Unsupported resource type"):
        _to_dict(42, api_client)


# ---------------------------------------------------------------------------
# _apply_resource / provision
# ---------------------------------------------------------------------------


def test_apply_resource_namespaced_and_cluster_scoped(applier):
    # Cluster-scoped Namespace should NOT get namespace param
    ns_manifest = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": "myns"},
    }

    applier._apply_resource(
        ns_manifest,
        field_manager="fm",
        force=False,
        namespace="ignored",
        timeout=10,
    )

    ns_calls = applier._test_ns.applied
    assert len(ns_calls) == 1
    assert "namespace" not in ns_calls[0]

    # Namespaced ConfigMap should get namespace if not set
    cm_manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "mycm"},
    }

    applier._apply_resource(
        cm_manifest,
        field_manager="fm",
        force=True,
        namespace="default",
        timeout=10,
    )

    cm_calls = applier._test_cm.applied
    assert len(cm_calls) == 1
    call = cm_calls[0]
    assert call["namespace"] == "default"
    assert call["field_manager"] == "fm"
    assert call["force"] is True
    assert call["_request_timeout"] == 10


def test_provision_orders_namespaces_and_builds_inventory(applier):
    manifests = [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm1"},
        },
        {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": "ns1"},
        },
    ]

    created, inventory = applier.provision(
        manifests,
        default_namespace="def",
        field_manager="fm",
    )

    assert len(created) == 2
    assert len(inventory) == 2

    # Namespace should be first in inventory
    assert inventory[0].kind == "Namespace"
    assert inventory[0].name == "ns1"
    assert inventory[0].namespace is None  # cluster-scoped

    # Then ConfigMap with default namespace filled in
    assert inventory[1].kind == "ConfigMap"
    assert inventory[1].name == "cm1"
    assert inventory[1].namespace == "def"


def test_provision_stop_on_error_true_raises_with_partial_inventory(applier):
    # cm1 applies OK, cm2 fails
    applier._test_cm.raise_on_patch["cm2"] = ApiException(
        status=500, reason="boom"
    )

    manifests = [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm1"},
        },
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm2"},
        },
    ]

    with pytest.raises(ProvisioningError) as exc:
        applier.provision(
            manifests,
            default_namespace="def",
            field_manager="fm",
            stop_on_error=True,
        )

    err = exc.value
    # cm1 should be in inventory, cm2 not
    assert len(err.inventory) == 1
    assert err.inventory[0].name == "cm1"
    # we recorded at least one error message
    assert err.errors
    assert "cm2" in err.errors[0]


def test_provision_stop_on_error_false_collects_all_errors(applier):
    # cm1 OK, cm2 + cm3 fail, but we continue
    applier._test_cm.raise_on_patch["cm2"] = ApiException(
        status=400, reason="bad"
    )
    applier._test_cm.raise_on_patch["cm3"] = RuntimeError("boom")

    manifests = [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm1"},
        },
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm2"},
        },
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cm3"},
        },
    ]

    with pytest.raises(ProvisioningError) as exc:
        applier.provision(
            manifests,
            default_namespace="def",
            field_manager="fm",
            stop_on_error=False,
        )

    err = exc.value
    # Only cm1 should have been added to inventory
    assert [item.name for item in err.inventory] == ["cm1"]
    # 2 errors collected
    assert len(err.errors) == 2
    assert "cm2" in err.errors[0]
    assert "cm3" in err.errors[1]


# ---------------------------------------------------------------------------
# delete_from_inventory
# ---------------------------------------------------------------------------


def test_delete_from_inventory_deletes_in_reverse_order_and_skips_namespaces(
    applier,
):
    dep_res = applier._test_dep
    cm_res = applier._test_cm

    inv = [
        ResourceInventoryItem(
            api_version="v1", kind="Namespace", namespace=None, name="ns1"
        ),
        ResourceInventoryItem(
            api_version="v1", kind="ConfigMap", namespace="ns", name="cm1"
        ),
        ResourceInventoryItem(
            api_version="apps/v1",
            kind="Deployment",
            namespace="ns",
            name="dep1",
        ),
    ]

    result: DeletionResult = applier.delete_from_inventory(inventory=inv)

    # stats
    assert result.deleted_count == 2
    assert result.skipped_count == 1
    assert result.failed_count == 0

    # Namespace is skipped
    assert any("Namespace/ns1" in r for r in result.skipped_resources)

    # Deletion should be in reverse order: dep1 then cm1
    assert dep_res.deleted[0]["name"] == "dep1"
    assert cm_res.deleted[0]["name"] == "cm1"


def test_delete_from_inventory_404_is_skipped_and_other_errors_are_failed(
    applier,
):
    res = applier._test_dyn.register("batch/v1", "Job", namespaced=True)
    # "missing" returns a 404, "bad" raises a 500
    res.raise_on_delete["missing"] = ApiException(
        status=404, reason="Not Found"
    )
    res.raise_on_delete["bad"] = ApiException(status=500, reason="Internal")

    inv = [
        ResourceInventoryItem(
            api_version="batch/v1", kind="Job", namespace="ns", name="missing"
        ),
        ResourceInventoryItem(
            api_version="batch/v1", kind="Job", namespace="ns", name="bad"
        ),
    ]

    result = applier.delete_from_inventory(inventory=inv)

    assert result.deleted_count == 0
    assert result.skipped_count == 1
    assert result.failed_count == 1

    # Check error messages contain resource names
    assert any("missing" in r for r in result.skipped_resources)
    assert any("bad" in r for r in result.failed_resources)


# ---------------------------------------------------------------------------
# GET / LIST
# ---------------------------------------------------------------------------


def test_get_resource_found_and_not_found(applier):
    pod_res = applier._test_pod

    pod = types.SimpleNamespace(
        metadata=types.SimpleNamespace(name="mypod"),
        status=None,
        spec=None,
    )
    pod_res.list_items = [pod]

    found = applier.get_resource(
        name="mypod",
        namespace="ns",
        kind="Pod",
        api_version="v1",
    )
    assert found is pod

    not_found = applier.get_resource(
        name="other",
        namespace="ns",
        kind="Pod",
        api_version="v1",
    )
    assert not_found is None


def test_get_resource_propagates_non_404_api_errors(applier):
    res = applier._test_dyn.register("v1", "Service", namespaced=True)

    def bad_get(**kwargs):
        raise ApiException(status=500, reason="boom")

    res.get = bad_get  # type: ignore[assignment]

    with pytest.raises(ApiException) as exc:
        applier.get_resource("svc", "ns", "Service", "v1")

    assert exc.value.status == 500


def test_list_resources_returns_items(applier):
    res = applier._test_dyn.register("v1", "Secret", namespaced=True)

    s1 = types.SimpleNamespace(
        metadata=types.SimpleNamespace(name="a", namespace="ns1")
    )
    s2 = types.SimpleNamespace(
        metadata=types.SimpleNamespace(name="b", namespace="ns1")
    )
    res.list_items = [s1, s2]

    out = applier.list_resources(
        kind="Secret",
        api_version="v1",
        namespace="ns1",
        label_selector="app=x",
    )

    # Our dummy does not filter by label; we only assert items are returned.
    assert len(out) == 2
    assert {o.metadata.name for o in out} == {"a", "b"}


# ---------------------------------------------------------------------------
# Waiters
# ---------------------------------------------------------------------------


def test_wait_for_deployment_ready_happy_path(applier, monkeypatch):
    # Simulate: first call not ready, second call ready
    not_ready = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "conditions": [
                    {"type": "Available", "status": "False"},
                ]
            }
        }
    )

    ready = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "conditions": [
                    {"type": "Available", "status": "True"},
                ]
            }
        }
    )

    sequence = [not_ready, ready]

    def fake_get_resource(name, namespace, kind, api_version):
        return sequence.pop(0) if sequence else ready

    monkeypatch.setattr(applier, "get_resource", fake_get_resource)

    obj = applier.wait_for_deployment_ready(
        name="dep",
        namespace="ns",
        timeout=5,
        check_interval=0,
    )
    assert obj is ready


def test_wait_for_deployment_ready_times_out(applier, monkeypatch):
    # Always returns an object that is never "Available"
    never_ready = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "conditions": [
                    {"type": "Available", "status": "False"},
                ]
            }
        }
    )

    monkeypatch.setattr(applier, "get_resource", lambda *a, **k: never_ready)

    start = time.time()
    with pytest.raises(RuntimeError, match="Deployment 'dep' not ready"):
        applier.wait_for_deployment_ready(
            name="dep",
            namespace="ns",
            timeout=0,  # immediate timeout
            check_interval=0,
        )
    assert time.time() - start < 1.0  # sanity check: didn't spin forever


def test_wait_for_service_loadbalancer_ip_happy_path(applier, monkeypatch):
    svc_obj = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "loadBalancer": {
                    "ingress": [{"ip": "1.2.3.4"}],
                }
            }
        }
    )

    monkeypatch.setattr(
        applier,
        "wait_for_resource_condition",
        lambda *a, **k: svc_obj,
    )

    host = applier.wait_for_service_loadbalancer_ip(
        name="svc",
        namespace="ns",
        timeout=5,
        check_interval=0,
    )
    assert host == "1.2.3.4"


def test_wait_for_service_loadbalancer_ip_but_no_host_raises(
    applier, monkeypatch
):
    svc_obj = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "loadBalancer": {
                    "ingress": [],
                }
            }
        }
    )

    monkeypatch.setattr(
        applier,
        "wait_for_resource_condition",
        lambda *a, **k: svc_obj,
    )

    with pytest.raises(RuntimeError, match="no external IP/hostname"):
        applier.wait_for_service_loadbalancer_ip(
            name="svc",
            namespace="ns",
            timeout=1,
            check_interval=0,
        )


def test_svc_lb_host_handles_ip_hostname_and_absence(applier):
    # via to_dict()
    svc_ip = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}]}},
        }
    )
    assert applier._svc_lb_host(svc_ip) == "1.2.3.4"

    # via hostname
    svc_hostname = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {
                "loadBalancer": {"ingress": [{"hostname": "lb.example.com"}]}
            },
        }
    )
    assert applier._svc_lb_host(svc_hostname) == "lb.example.com"

    # no ingress
    svc_none = types.SimpleNamespace(
        to_dict=lambda: {
            "status": {"loadBalancer": {"ingress": []}},
        }
    )
    assert applier._svc_lb_host(svc_none) is None

    # direct dict without to_dict
    svc_dict = {
        "status": {"loadBalancer": {"ingress": [{"ip": "5.6.7.8"}]}},
    }
    assert applier._svc_lb_host(svc_dict) == "5.6.7.8"
