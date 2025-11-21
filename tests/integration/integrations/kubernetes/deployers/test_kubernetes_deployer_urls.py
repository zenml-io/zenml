"""Unit tests for Kubernetes deployer URL selection and discovery."""

from typing import Any, Dict, Optional

import pytest

from zenml.deployers.exceptions import DeployerError
from zenml.enums import KubernetesServiceType, KubernetesUrlPreference
from zenml.integrations.kubernetes.deployers.kubernetes_deployer import (
    KubernetesDeployer,
)
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerSettings,
)
from zenml.integrations.kubernetes.k8s_applier import ResourceInventoryItem


class _FakeApplier:
    """Minimal fake applier to return canned resources."""

    def __init__(self, resources: Dict[Any, Any]) -> None:
        self.resources = resources

    def get_resource(
        self,
        name: str,
        namespace: Optional[str],
        kind: str,
        api_version: str,
    ) -> Optional[Any]:
        return self.resources.get((kind, api_version, name, namespace or ""))


class _FakeCoreApi:
    """Placeholder CoreV1Api stub (not used in these tests)."""

    pass


class _TestDeployer(KubernetesDeployer):
    """Test subclass to override dependency properties."""

    def __init__(self, applier: _FakeApplier) -> None:
        # Skip base init; we control dependencies manually.
        self._applier = applier  # type: ignore[attr-defined]

    @property  # type: ignore[override]
    def k8s_applier(self) -> _FakeApplier:
        return self._applier

    @property  # type: ignore[override]
    def k8s_core_api(self) -> _FakeCoreApi:
        return _FakeCoreApi()


def _make_deployer_with_resources(
    resources: Dict[Any, Any],
) -> KubernetesDeployer:
    """Create a deployer instance wired with fake dependencies."""
    return _TestDeployer(applier=_FakeApplier(resources))


def test_select_url_pref_not_found_includes_discovered_types() -> None:
    """Explicit preference errors when URL type is missing and lists discovered."""
    deployer = KubernetesDeployer.__new__(KubernetesDeployer)
    settings = KubernetesDeployerSettings(
        url_preference=KubernetesUrlPreference.INGRESS
    )
    discovered = {
        "gateway_api": None,
        "ingress": None,
        "load_balancer": "http://1.2.3.4:8000",
        "node_port": None,
        "cluster_ip": "http://svc.ns.svc.cluster.local:8000",
    }

    with pytest.raises(DeployerError) as excinfo:
        deployer._select_url(
            discovered_urls=discovered,
            settings=settings,
            deployment_name="demo",
        )

    message = str(excinfo.value)
    assert "ingress" in message.lower()
    assert "demo" in message
    assert "load_balancer" in message or "cluster_ip" in message


def test_select_url_auto_prefers_load_balancer() -> None:
    """AUTO preference mirrors service_type ordering."""
    deployer = KubernetesDeployer.__new__(KubernetesDeployer)
    settings = KubernetesDeployerSettings(
        service_type=KubernetesServiceType.LOAD_BALANCER
    )
    discovered = {
        "gateway_api": None,
        "ingress": None,
        "load_balancer": "http://1.2.3.4:8000",
        "node_port": "http://node:30000",
        "cluster_ip": "http://svc.ns.svc.cluster.local:8000",
    }

    url = deployer._select_url(
        discovered_urls=discovered,
        settings=settings,
        deployment_name="demo",
    )

    assert url == "http://1.2.3.4:8000"


def test_discover_urls_finds_ingress_url() -> None:
    """Ingress discovery returns the ingress URL when configured."""
    service_inventory = ResourceInventoryItem(
        kind="Service",
        api_version="v1",
        namespace="ns",
        name="weather",
    )
    ingress_inventory = ResourceInventoryItem(
        kind="Ingress",
        api_version="networking.k8s.io/v1",
        namespace="ns",
        name="weather-ing",
    )

    resources = {
        ("Service", "v1", "weather", "ns"): {
            "metadata": {"name": "weather"},
            "spec": {
                "type": "ClusterIP",
                "ports": [{"port": 8000}],
            },
        },
        ("Ingress", "networking.k8s.io/v1", "weather-ing", "ns"): {
            "spec": {
                "rules": [
                    {
                        "host": "weather.company.com",
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "backend": {
                                        "service": {"name": "weather"},
                                    },
                                }
                            ]
                        },
                    }
                ]
            }
        },
    }
    deployer = _make_deployer_with_resources(resources)

    discovered = deployer._discover_urls(
        inventory=[service_inventory, ingress_inventory],
        namespace="ns",
    )

    assert discovered["ingress"] == "http://weather.company.com/"
    assert (
        discovered["cluster_ip"] == "http://weather.ns.svc.cluster.local:8000"
    )
