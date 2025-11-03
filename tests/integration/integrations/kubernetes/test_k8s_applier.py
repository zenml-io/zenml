from types import SimpleNamespace

import pytest
from kubernetes.client.rest import ApiException

from zenml.integrations.kubernetes import k8s_applier
from zenml.integrations.kubernetes.k8s_applier import KubernetesApplier


class DummyResource:
    def __init__(
        self, namespaced: bool, exists: bool, delete_404: bool = False
    ):
        self.namespaced = namespaced
        self.exists = exists
        self.delete_404 = delete_404
        self.create_calls = []
        self.patch_calls = []
        self.delete_calls = []

    def get(self, **_kwargs):
        if self.exists:
            return SimpleNamespace()
        raise ApiException(status=404)

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        self.exists = True
        return SimpleNamespace()

    def patch(self, **kwargs):
        self.patch_calls.append(kwargs)
        return SimpleNamespace()

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.delete_404:
            raise ApiException(status=404)
        return None


@pytest.fixture
def dynamic_client_fixture(monkeypatch: pytest.MonkeyPatch):
    resource_map: dict[tuple[str, str], DummyResource] = {}

    class Resources:
        def get(self, api_version: str, kind: str) -> DummyResource:
            try:
                return resource_map[(api_version, kind)]
            except KeyError as exc:
                raise k8s_applier.ResourceNotFoundError from exc

    class DummyDynamicClient:
        def __init__(self, _api_client):
            self.resources = Resources()

    monkeypatch.setattr(
        "zenml.integrations.kubernetes.k8s_applier.dynamic.DynamicClient",
        lambda api_client: DummyDynamicClient(api_client),
    )

    return resource_map


def test_apply_yaml_creates_namespaced_resource(
    dynamic_client_fixture,
) -> None:
    dynamic_client_fixture[("example/v1", "Example")] = DummyResource(
        namespaced=True, exists=False
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: example/v1
kind: Example
metadata:
  name: sample
  namespace: default
spec:
  value: 1
"""

    results = applier.apply_yaml(yaml_content)

    assert len(results) == 1
    resource = dynamic_client_fixture[("example/v1", "Example")]
    assert len(resource.patch_calls) == 1
    assert resource.patch_calls[0]["namespace"] == "default"


def test_apply_yaml_updates_existing_resource(dynamic_client_fixture) -> None:
    dynamic_client_fixture[("example/v1", "Example")] = DummyResource(
        namespaced=True, exists=True
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: example/v1
kind: Example
metadata:
  name: sample
  namespace: default
spec:
  value: 1
"""

    results = applier.apply_yaml(yaml_content, dry_run=True)

    assert len(results) == 1
    resource = dynamic_client_fixture[("example/v1", "Example")]
    assert len(resource.patch_calls) == 1
    assert resource.patch_calls[0]["dry_run"] == "All"


def test_apply_yaml_cluster_scoped_resource(dynamic_client_fixture) -> None:
    dynamic_client_fixture[("rbac.authorization.k8s.io/v1", "ClusterRole")] = (
        DummyResource(namespaced=False, exists=False)
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: demo
rules: []
"""

    results = applier.apply_yaml(yaml_content)

    assert len(results) == 1
    resource = dynamic_client_fixture[
        ("rbac.authorization.k8s.io/v1", "ClusterRole")
    ]
    assert len(resource.patch_calls) == 1
    assert "namespace" not in resource.patch_calls[0]


def test_apply_yaml_missing_name_raises(dynamic_client_fixture) -> None:
    dynamic_client_fixture[("example/v1", "Example")] = DummyResource(
        namespaced=True, exists=False
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = "apiVersion: example/v1\nkind: Example\nmetadata: {}\n"

    with pytest.raises(ValueError, match="metadata.name"):
        applier.apply_yaml(yaml_content)


def test_apply_resource_invalid_type(dynamic_client_fixture) -> None:
    applier = KubernetesApplier(api_client=object())

    with pytest.raises(ValueError):
        applier.apply_resource(42)  # type: ignore[arg-type]


def test_apply_resource_preserves_api_version_and_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeApiClient:
        configuration = SimpleNamespace()  # Required by DynamicClient

        def sanitize_for_serialization(self, resource):
            return {"metadata": {"name": "demo"}}

    class FakeResource:
        api_version = "apps/v1"
        kind = "Deployment"

        def to_dict(self):
            return {"metadata": {"name": "demo"}}

    captured: dict[str, object] = {}

    # Mock DynamicClient to avoid initialization errors
    class FakeDynamicClient:
        def __init__(self, api_client):
            pass

    monkeypatch.setattr(
        "zenml.integrations.kubernetes.k8s_applier.dynamic.DynamicClient",
        FakeDynamicClient,
    )

    applier = KubernetesApplier(api_client=FakeApiClient())

    # Mock ssa_apply instead of apply_yaml (apply_resource now uses ssa_apply)
    def fake_ssa_apply(resource: dict, **kwargs) -> None:
        captured["resource"] = resource
        captured["dry_run"] = kwargs.get("dry_run", False)

    monkeypatch.setattr(
        applier,
        "ssa_apply",
        fake_ssa_apply,
        raising=False,
    )

    applier.apply_resource(FakeResource(), dry_run=False)

    assert "resource" in captured
    assert captured["resource"]["apiVersion"] == "apps/v1"
    assert captured["resource"]["kind"] == "Deployment"
    assert captured["dry_run"] is False


def test_apply_resource_normalizes_metadata_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeApiClient:
        configuration = SimpleNamespace()  # Required by DynamicClient

        def sanitize_for_serialization(self, resource):
            return {
                "api_version": "batch/v1",
                "kind": "Job",
                "metadata": {"name": "demo"},
            }

    class FakeResource:
        def to_dict(self):
            return {"metadata": {"name": "demo"}}

    # Mock DynamicClient to avoid initialization errors
    class FakeDynamicClient:
        def __init__(self, api_client):
            pass

    monkeypatch.setattr(
        "zenml.integrations.kubernetes.k8s_applier.dynamic.DynamicClient",
        FakeDynamicClient,
    )

    applier = KubernetesApplier(api_client=FakeApiClient())
    captured_resource: dict[str, object] = {}

    # Mock ssa_apply instead of apply_yaml (apply_resource now uses ssa_apply)
    def fake_ssa_apply(resource: dict, **kwargs) -> None:
        captured_resource.update(resource)

    monkeypatch.setattr(
        applier,
        "ssa_apply",
        fake_ssa_apply,
        raising=False,
    )

    applier.apply_resource(FakeResource(), dry_run=True)

    assert captured_resource["apiVersion"] == "batch/v1"
    assert "api_version" not in captured_resource
    assert captured_resource["kind"] == "Job"


def test_apply_resource_raises_for_missing_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeApiClient:
        configuration = SimpleNamespace()  # Required by DynamicClient

        def sanitize_for_serialization(self, resource):
            return {"metadata": {"name": "demo"}}

    class IncompleteResource:
        def to_dict(self):
            return {"metadata": {"name": "demo"}}

    # Mock DynamicClient to avoid initialization errors
    class FakeDynamicClient:
        def __init__(self, api_client):
            pass

    monkeypatch.setattr(
        "zenml.integrations.kubernetes.k8s_applier.dynamic.DynamicClient",
        FakeDynamicClient,
    )

    applier = KubernetesApplier(api_client=FakeApiClient())

    with pytest.raises(ValueError) as exc_info:
        applier.apply_resource(IncompleteResource())

    assert "apiVersion" in str(exc_info.value)


def test_delete_resource_handles_404(dynamic_client_fixture) -> None:
    resource = DummyResource(namespaced=True, exists=False, delete_404=True)
    dynamic_client_fixture[("example/v1", "Example")] = resource

    applier = KubernetesApplier(api_client=object())
    applier.delete_resource("sample", "default", "Example", "example/v1")

    assert len(resource.delete_calls) == 1


def test_get_resource_returns_none_for_404(dynamic_client_fixture) -> None:
    resource = DummyResource(namespaced=True, exists=False)
    dynamic_client_fixture[("example/v1", "Example")] = resource

    applier = KubernetesApplier(api_client=object())
    result = applier.get_resource("sample", "default", "Example", "example/v1")
    assert result is None


def test_wait_for_resource_condition_timeout(
    dynamic_client_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applier = KubernetesApplier(api_client=object())

    call_counter = {"count": 0}

    def fake_get_resource(*_args, **_kwargs):
        call_counter["count"] += 1
        return SimpleNamespace()

    applier.get_resource = fake_get_resource  # type: ignore[assignment]

    times = iter([0, 0.5, 2])

    def fake_time() -> float:
        try:
            return next(times)
        except StopIteration:
            return 2

    monkeypatch.setattr(k8s_applier.time, "time", fake_time)
    monkeypatch.setattr(k8s_applier.time, "sleep", lambda _s: None)

    with pytest.raises(RuntimeError):
        applier.wait_for_resource_condition(
            name="sample",
            namespace="default",
            kind="Example",
            api_version="example/v1",
            condition_fn=lambda _obj: False,
            timeout=1,
            check_interval=1,
            resource_description="Example",
        )

    assert call_counter["count"] >= 1


def test_wait_for_deployment_ready_delegates(
    dynamic_client_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applier = KubernetesApplier(api_client=object())
    recorded: dict[str, object] = {}

    def fake_wait_for_resource_condition(**kwargs):
        recorded["kwargs"] = kwargs
        return SimpleNamespace()

    monkeypatch.setattr(
        applier,
        "wait_for_resource_condition",
        fake_wait_for_resource_condition,
        raising=False,
    )

    applier.wait_for_deployment_ready(
        "demo", "ns", timeout=10, check_interval=2
    )

    assert "kwargs" in recorded


def test_wait_for_service_loadbalancer_ip_success(
    dynamic_client_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applier = KubernetesApplier(api_client=object())

    service = SimpleNamespace(
        spec=SimpleNamespace(ports=[SimpleNamespace(port=80)]),
        status=SimpleNamespace(
            load_balancer=SimpleNamespace(
                ingress=[SimpleNamespace(ip="1.2.3.4", hostname=None)]
            )
        ),
    )

    monkeypatch.setattr(
        applier,
        "wait_for_resource_condition",
        lambda **_kwargs: service,
        raising=False,
    )

    ip = applier.wait_for_service_loadbalancer_ip(
        "svc", "ns", timeout=10, check_interval=1
    )
    assert ip == "1.2.3.4"


def test_wait_for_service_loadbalancer_ip_failure(
    dynamic_client_fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applier = KubernetesApplier(api_client=object())
    service = SimpleNamespace(
        spec=SimpleNamespace(ports=[SimpleNamespace(port=80)]),
        status=SimpleNamespace(load_balancer=SimpleNamespace(ingress=[])),
    )

    monkeypatch.setattr(
        applier,
        "wait_for_resource_condition",
        lambda **_kwargs: service,
        raising=False,
    )

    with pytest.raises(
        RuntimeError, match="no LoadBalancer IP/hostname found"
    ):
        applier.wait_for_service_loadbalancer_ip(
            "svc", "ns", timeout=10, check_interval=1
        )


def test_apply_yaml_multi_document(dynamic_client_fixture) -> None:
    """Test that apply_yaml handles multi-document YAML."""
    dynamic_client_fixture[("v1", "ConfigMap")] = DummyResource(
        namespaced=True, exists=False
    )
    dynamic_client_fixture[("v1", "Secret")] = DummyResource(
        namespaced=True, exists=False
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
  namespace: default
data:
  key: value
---
apiVersion: v1
kind: Secret
metadata:
  name: secret1
  namespace: default
type: Opaque
data:
  password: cGFzcw==
"""

    results = applier.apply_yaml(yaml_content)

    assert len(results) == 2
    configmap = dynamic_client_fixture[("v1", "ConfigMap")]
    assert len(configmap.patch_calls) == 1
    secret = dynamic_client_fixture[("v1", "Secret")]
    assert len(secret.patch_calls) == 1


def test_delete_from_yaml_multi_document(dynamic_client_fixture) -> None:
    """Test that delete_from_yaml handles multi-document YAML."""
    cm_resource = DummyResource(namespaced=True, exists=True, delete_404=False)
    secret_resource = DummyResource(
        namespaced=True, exists=True, delete_404=False
    )
    dynamic_client_fixture[("v1", "ConfigMap")] = cm_resource
    dynamic_client_fixture[("v1", "Secret")] = secret_resource

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
  namespace: default
---
apiVersion: v1
kind: Secret
metadata:
  name: secret1
  namespace: default
"""

    applier.delete_from_yaml(yaml_content, namespace="default")

    assert len(cm_resource.delete_calls) == 1
    assert len(secret_resource.delete_calls) == 1


def test_ensure_namespace_alignment_strips_cluster_resource_namespace(
    dynamic_client_fixture,
) -> None:
    """Test that ensure_namespace_alignment removes namespace from cluster-scoped resources."""
    dynamic_client_fixture[("rbac.authorization.k8s.io/v1", "ClusterRole")] = (
        DummyResource(namespaced=False, exists=False)
    )

    applier = KubernetesApplier(api_client=object())
    resource_dict = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRole",
        "metadata": {
            "name": "demo",
            "namespace": "should-be-removed",
        },
        "rules": [],
    }

    applier.ensure_namespace_alignment(
        resource_dict=resource_dict,
        namespace="default",
        deployment_name="test-deployment",
    )

    assert "namespace" not in resource_dict["metadata"]


def test_ensure_namespace_alignment_adds_namespace_to_namespaced_resource(
    dynamic_client_fixture,
) -> None:
    """Test that ensure_namespace_alignment adds namespace to namespaced resources."""
    dynamic_client_fixture[("v1", "ConfigMap")] = DummyResource(
        namespaced=True, exists=False
    )

    applier = KubernetesApplier(api_client=object())
    resource_dict = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "config1"},
        "data": {},
    }

    applier.ensure_namespace_alignment(
        resource_dict=resource_dict,
        namespace="my-namespace",
        deployment_name="test-deployment",
    )

    assert resource_dict["metadata"]["namespace"] == "my-namespace"


def test_apply_yaml_missing_namespace_raises(dynamic_client_fixture) -> None:
    """Test that apply_yaml raises when namespace is required but missing."""
    dynamic_client_fixture[("v1", "ConfigMap")] = DummyResource(
        namespaced=True, exists=False
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
data:
  key: value
"""

    with pytest.raises(
        ValueError, match="requires an explicit namespace parameter"
    ):
        applier.apply_yaml(yaml_content)


def test_delete_from_yaml_missing_namespace_raises(
    dynamic_client_fixture,
) -> None:
    """Test that delete_from_yaml raises when namespace is required but missing."""
    dynamic_client_fixture[("v1", "ConfigMap")] = DummyResource(
        namespaced=True, exists=True
    )

    applier = KubernetesApplier(api_client=object())
    yaml_content = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
"""

    with pytest.raises(
        ValueError, match="requires an explicit namespace parameter"
    ):
        applier.delete_from_yaml(yaml_content)


def test_ensure_namespace_alignment_allows_unknown_resources(
    dynamic_client_fixture,
) -> None:
    """Test that ensure_namespace_alignment allows unknown CRD resources by default."""
    applier = KubernetesApplier(api_client=object())

    # Simulate a CRD that doesn't exist yet
    resource_dict = {
        "apiVersion": "custom.io/v1",
        "kind": "CustomResource",
        "metadata": {"name": "my-resource"},
    }

    # Should not raise, should add namespace
    applier.ensure_namespace_alignment(
        resource_dict=resource_dict,
        namespace="my-namespace",
        deployment_name="test-deployment",
        allow_unknown_resources=True,
    )

    assert resource_dict["metadata"]["namespace"] == "my-namespace"


def test_ensure_namespace_alignment_strict_mode_unknown_raises(
    dynamic_client_fixture,
) -> None:
    """Test that ensure_namespace_alignment raises for unknown resources in strict mode."""
    applier = KubernetesApplier(api_client=object())

    # Simulate a CRD that doesn't exist yet
    resource_dict = {
        "apiVersion": "custom.io/v1",
        "kind": "CustomResource",
        "metadata": {"name": "my-resource"},
    }

    # Should raise in strict mode
    with pytest.raises(ValueError, match="Cannot determine scope"):
        applier.ensure_namespace_alignment(
            resource_dict=resource_dict,
            namespace="my-namespace",
            deployment_name="test-deployment",
            allow_unknown_resources=False,
        )
