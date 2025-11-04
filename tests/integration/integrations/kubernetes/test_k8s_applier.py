"""Unit tests for KubernetesApplier."""

from unittest.mock import Mock, patch

import pytest
from kubernetes.client.exceptions import ApiException

from zenml.integrations.kubernetes.k8s_applier import KubernetesApplier


class TestInitialization:
    """Test applier initialization."""

    def test_init_with_api_client(self, mock_k8s_api_client):
        """Test initialization with API client."""
        with patch("zenml.integrations.kubernetes.k8s_applier.DynamicClient"):
            applier = KubernetesApplier(mock_k8s_api_client)
            assert applier.api_client == mock_k8s_api_client
            assert applier.dynamic is not None


class TestProvision:
    """Test resource provisioning."""

    def test_provision_single_resource(
        self, mock_k8s_api_client, mock_dynamic_client
    ):
        """Test basic resource provisioning."""
        mock_resource = Mock()
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)
        mock_dynamic_client.server_side_apply = Mock(return_value=Mock())

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            manifest = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test-config"},
            }

            results = applier.provision(
                [manifest],
                default_namespace="default",
                dry_run=False,
            )

            assert len(results) == 1

    def test_provision_dry_run(self, mock_k8s_api_client, mock_dynamic_client):
        """Test dry-run provisioning."""
        mock_resource = Mock()
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)
        mock_dynamic_client.server_side_apply = Mock(return_value=Mock())

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            manifest = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test"},
            }

            applier.provision(
                [manifest],
                default_namespace="default",
                dry_run=True,
            )

            call_kwargs = mock_dynamic_client.server_side_apply.call_args[1]
            assert call_kwargs.get("dry_run") == "All"

    def test_provision_api_exception(
        self, mock_k8s_api_client, mock_dynamic_client
    ):
        """Test provision re-raises API exceptions."""
        mock_resource = Mock()
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)
        mock_dynamic_client.server_side_apply = Mock(
            side_effect=ApiException(
                status=500, reason="Internal Server Error"
            )
        )

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            manifest = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test"},
            }

            with pytest.raises(ApiException):
                applier.provision(
                    [manifest],
                    default_namespace="default",
                    dry_run=False,
                )


class TestWaitConditions:
    """Test wait condition helpers."""

    def test_wait_for_deployment_ready(
        self, mock_k8s_api_client, mock_dynamic_client, mock_deployment_object
    ):
        """Test waiting for deployment to be ready."""
        mock_resource = Mock()
        mock_resource.get = Mock(return_value=mock_deployment_object)
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            deployment = applier.wait_for_deployment_ready(
                name="test-deployment",
                namespace="default",
                timeout=5,
            )

            assert deployment is not None

    def test_wait_timeout(self, mock_k8s_api_client, mock_dynamic_client):
        """Test wait timeout raises RuntimeError."""
        mock_resource = Mock()
        mock_resource.get = Mock(return_value=None)
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            with pytest.raises(RuntimeError, match="not ready within"):
                applier.wait_for_resource_condition(
                    kind="Deployment",
                    name="nonexistent",
                    namespace="default",
                    api_version="apps/v1",
                    condition_fn=lambda x: True,
                    timeout=2,
                    check_interval=1,
                )


class TestDeleteOperations:
    """Test delete operations."""

    def test_delete_by_label_selector(
        self, mock_k8s_api_client, mock_dynamic_client
    ):
        """Test deleting resources by label selector."""
        mock_list_result = Mock()
        mock_list_result.items = [Mock(metadata=Mock(name="test-deployment"))]

        mock_resource = Mock()
        mock_resource.get = Mock(return_value=mock_list_result)
        mock_resource.delete = Mock()
        mock_resource.namespaced = True

        mock_dynamic_client.resources.get = Mock(return_value=mock_resource)

        with patch(
            "zenml.integrations.kubernetes.k8s_applier.DynamicClient",
            return_value=mock_dynamic_client,
        ):
            applier = KubernetesApplier(mock_k8s_api_client)

            count = applier.delete_by_label_selector(
                label_selector="app=test",
                namespace="default",
                dry_run=False,
                kinds=[("Deployment", "apps/v1")],
            )

            assert count == 1


class TestHelperMethods:
    """Test helper methods."""

    def test_flatten_items(self):
        """Test flattening Kubernetes List resources."""
        from zenml.integrations.kubernetes.k8s_applier import _flatten_items

        list_resource = {
            "kind": "List",
            "items": [
                {"kind": "ConfigMap", "metadata": {"name": "cm1"}},
                {"kind": "ConfigMap", "metadata": {"name": "cm2"}},
            ],
        }

        result = list(_flatten_items([list_resource]))
        assert len(result) == 2

    def test_to_dict_from_dict(self, mock_k8s_api_client):
        """Test _to_dict with dictionary input."""
        from zenml.integrations.kubernetes.k8s_applier import _to_dict

        input_dict = {"kind": "ConfigMap"}
        result = _to_dict(input_dict, mock_k8s_api_client)

        assert result == input_dict
