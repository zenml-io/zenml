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
import types

import pytest
from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

# Import the module so we can monkeypatch its DynamicClient reference
from zenml.integrations.kubernetes import k8s_applier as k8s_applier_module
from zenml.integrations.kubernetes.k8s_applier import (
    KubernetesApplier,
    ResourceInventoryItem,
    _flatten_items,
    _to_dict,
)


class DummyApiClient(k8s_client.ApiClient):
    """Minimal ApiClient stub for sanitize_for_serialization."""

    def sanitize_for_serialization(self, obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return obj


class DummyModel:
    def __init__(self, api_version="v1", kind="ConfigMap", name="cm"):
        self.api_version = api_version
        self.kind = kind
        self.metadata = types.SimpleNamespace(name=name)

    def to_dict(self):
        return {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": {"name": self.metadata.name},
        }


class DummyResource:
    """Fake dynamic resource wrapper implementing the subset used by KubernetesApplier."""

    def __init__(self, kind: str, api_version: str, namespaced: bool = True):
        self.kind = kind
        self.api_version = api_version
        self.namespaced = namespaced
        self.applied = []
        self.deleted = []
        self.list_items = []

    # Server-side apply / patch
    def patch(self, **kwargs):
        self.applied.append(kwargs)
        name = kwargs.get("name")
        namespace = kwargs.get("namespace")

        def _to_dict():
            return {
                "apiVersion": self.api_version,
                "kind": self.kind,
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                },
            }

        return types.SimpleNamespace(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata={"name": name, "namespace": namespace},
            to_dict=_to_dict,
        )

    # get() is used for:
    # - get_resource (by name)
    # - list_resources (when called as get(..., namespace=..., label_selector=...))
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

    # delete() is used by delete_from_inventory
    def delete(self, **kwargs):
        name = kwargs["name"]
        self.deleted.append(kwargs)
        # simulate 404 for a specific sentinel if needed
        if name == "missing":
            raise ApiException(status=404, reason="Not Found")


class DummyDynamic:
    """In-memory DynamicClient-like registry.

    KubernetesApplier only relies on `dynamic.resources.get(api_version=..., kind=...)`.
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
        # Return an object that supports .get(api_version=..., kind=...)
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

    # Fake DynamicClient that KubernetesApplier.__init__ will use.
    # IMPORTANT: This prevents any HTTP / discovery against a real cluster.
    class FakeDynamicClient:
        def __init__(self, _api_client):
            self._dyn = dyn
            self.resources = dyn.resources

    # Patch the symbol used in k8s_applier.py
    monkeypatch.setattr(k8s_applier_module, "DynamicClient", FakeDynamicClient)

    # Now this is safe: it will use FakeDynamicClient
    k = KubernetesApplier(api_client=api_client)

    # Expose handles for assertions in tests
    k._test_dyn = dyn
    k._test_ns = ns_res
    k._test_cm = cm_res
    k._test_dep = dep_res

    return k


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_flatten_items_basic():
    objs = [
        {"kind": "ConfigMap", "metadata": {"name": "a"}},
        {
            "kind": "List",
            "items": [
                {"kind": "ConfigMap", "metadata": {"name": "b"}},
                {"kind": "Secret", "metadata": {"name": "c"}},
            ],
        },
    ]

    out = list(_flatten_items(objs))
    assert len(out) == 3
    assert {o["metadata"]["name"] for o in out} == {"a", "b", "c"}


def test_to_dict_with_dict(api_client):
    obj = {"apiVersion": "v1", "kind": "ConfigMap"}
    out = _to_dict(obj, api_client)
    assert out is obj


def test_to_dict_with_model_normalizes_api_version(api_client):
    model = DummyModel(api_version="v1", kind="ConfigMap", name="cm1")
    out = _to_dict(model, api_client)
    assert out["apiVersion"] == "v1"
    assert out["kind"] == "ConfigMap"
    assert out["metadata"]["name"] == "cm1"


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
        force=False,
        namespace="default",
        timeout=10,
    )

    cm_calls = applier._test_cm.applied
    assert len(cm_calls) == 1
    assert cm_calls[0]["namespace"] == "default"


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

    # Namespace should be first
    assert inventory[0].kind == "Namespace"
    assert inventory[0].name == "ns1"

    # Then ConfigMap with default namespace filled in
    assert inventory[1].kind == "ConfigMap"
    assert inventory[1].name == "cm1"
    assert inventory[1].namespace == "def"


# ---------------------------------------------------------------------------
# delete_from_inventory
# ---------------------------------------------------------------------------


def test_delete_from_inventory_respects_reverse_order_and_namespaces(applier):
    # Register deployment resource used for deletion
    dep_res = applier._test_dyn.register(
        "apps/v1", "Deployment", namespaced=True
    )

    inv = [
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

    deleted = applier.delete_from_inventory(
        inventory=inv,
        propagation_policy="Foreground",
    )

    assert deleted == 2

    # Deletion should be in reverse order: dep1 then cm1
    assert dep_res.deleted[0]["name"] == "dep1"
    assert applier._test_cm.deleted[0]["name"] == "cm1"


# ---------------------------------------------------------------------------
# GET / LIST
# ---------------------------------------------------------------------------


def test_get_resource_found_and_not_found(applier):
    pod_res = applier._test_dyn.register("v1", "Pod", namespaced=True)

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
