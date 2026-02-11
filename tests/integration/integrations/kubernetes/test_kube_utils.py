"""Tests for Kubernetes utility helpers."""

from zenml.integrations.kubernetes import kube_utils


def test_build_gateway_api_url_handles_https_listener() -> None:
    """Gateway URL builder respects HTTPS listeners and hostnames."""
    gateway = {
        "status": {
            "listeners": [
                {
                    "name": "web",
                    "protocol": "HTTPS",
                }
            ]
        }
    }
    httproute = {
        "spec": {
            "hostnames": ["api.example.com"],
            "rules": [
                {
                    "matches": [
                        {
                            "path": {"type": "PathPrefix", "value": "/"},
                        }
                    ]
                }
            ],
            "parentRefs": [{"name": "web"}],
        }
    }

    url = kube_utils.build_gateway_api_url(
        gateway=gateway,
        httproute=httproute,
    )

    assert url == "https://api.example.com/"


def test_build_gateway_api_url_returns_none_without_hosts() -> None:
    """Gracefully returns None when no hostnames are present."""
    gateway = {"status": {"listeners": []}}
    httproute = {"spec": {"hostnames": [], "rules": []}}

    assert (
        kube_utils.build_gateway_api_url(gateway=gateway, httproute=httproute)
        is None
    )
