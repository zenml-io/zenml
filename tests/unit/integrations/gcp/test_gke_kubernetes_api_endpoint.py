"""Tests for GKE Kubernetes API endpoint resolution in the GCP service connector."""

import pytest
from google.cloud.container_v1.types import Cluster as GKECluster

from zenml.exceptions import AuthorizationException
from zenml.integrations.gcp.service_connectors.gcp_service_connector import (
    GCPServiceConnector,
)


def _cluster(
    *,
    endpoint: str = "10.0.0.1",
    cluster_ca: str = "Y2x1c3Rlci1jYQ==",
    dns_endpoint: str | None = None,
) -> GKECluster:
    cluster = GKECluster(
        endpoint=endpoint,
        master_auth=GKECluster.MasterAuth(cluster_ca_certificate=cluster_ca),
    )
    if dns_endpoint is not None:
        cluster.control_plane_endpoints_config.dns_endpoint_config.endpoint = (
            dns_endpoint
        )
    return cluster


def test_prefers_dns_endpoint_over_ip_endpoint() -> None:
    cluster = _cluster(
        endpoint="10.128.0.13",
        dns_endpoint="gke-abc-123.europe-west4.gke.goog",
    )

    server, ca_cert = GCPServiceConnector._resolve_gke_kubernetes_api_connection(
        cluster
    )

    assert server == "https://gke-abc-123.europe-west4.gke.goog"
    assert ca_cert is None


def test_falls_back_to_ip_endpoint_without_dns() -> None:
    cluster = _cluster(endpoint="34.1.2.3", cluster_ca="Y2E=")

    server, ca_cert = GCPServiceConnector._resolve_gke_kubernetes_api_connection(
        cluster
    )

    assert server == "https://34.1.2.3"
    assert ca_cert == "Y2E="


def test_raises_when_no_endpoint_is_available() -> None:
    cluster = _cluster(endpoint="")

    with pytest.raises(AuthorizationException):
        GCPServiceConnector._resolve_gke_kubernetes_api_connection(cluster)
