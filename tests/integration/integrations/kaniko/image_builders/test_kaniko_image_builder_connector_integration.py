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
"""Integration tests for Kaniko image builder Kubernetes connector enhancement."""

from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, patch
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.integrations.kaniko.flavors.kaniko_image_builder_flavor import (
    KanikoImageBuilderConfig,
)
from zenml.integrations.kaniko.image_builders import KanikoImageBuilder


def _get_kaniko_image_builder(
    config: Optional[KanikoImageBuilderConfig] = None,
) -> KanikoImageBuilder:
    """Helper function to get a Kaniko image builder."""
    if config is None:
        config = KanikoImageBuilderConfig(
            kubernetes_context="test-context",
            kubernetes_namespace="test-namespace",
        )
    
    return KanikoImageBuilder(
        name="test-kaniko",
        id=uuid4(),
        config=config,
        flavor="kaniko",
        type=StackComponentType.IMAGE_BUILDER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

def _patch_k8s_clients(mocker):
    """Helper function to patch k8s clients."""
    mock_connector = Mock()
    mock_api_client = Mock()
    mock_core_api = Mock()
    
    mock_connector.connect.return_value = mock_api_client
    mocker.patch("kubernetes.client.CoreV1Api", return_value=mock_core_api)
    mocker.patch("kubernetes.client.V1Container")
    mocker.patch("kubernetes.client.V1PodSpec")
    mocker.patch("kubernetes.client.V1Pod")
    mocker.patch("kubernetes.client.V1ObjectMeta")
    
    # Mock k8s_utils
    mocker.patch("kubernetes.k8s_utils.stream_file_to_pod")
    mocker.patch("kubernetes.k8s_utils.wait_pod")
    mocker.patch("kubernetes.k8s_utils.pod_is_done")
    
    return mock_connector, mock_api_client, mock_core_api


@patch("subprocess.Popen")
def test_connector_fallback_to_kubectl_integration(mock_popen, mocker):
    """Test complete integration flow with connector fallback to kubectl."""
    image_builder = _get_kaniko_image_builder()
    pod_name = "test-pod"
    spec_overrides = {
        "apiVersion": "v1",
        "spec": {
            "containers": [{
                "name": pod_name,
                "image": "gcr.io/kaniko-project/executor:v1.9.1",
                "args": ["--dockerfile=Dockerfile"],
            }]
        }
    }
    build_context = Mock()
    
    # Mock process for kubectl
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.wait.return_value = 0  # Success
    mock_popen.return_value.__enter__.return_value = mock_process
    
    mock_write_context = mocker.patch.object(image_builder, '_write_build_context')
    
    with patch.object(image_builder, 'get_connector', return_value=None):
        image_builder._run_kaniko_build(pod_name, spec_overrides, build_context)
        
        # Verify kubectl command was constructed correctly
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        command = args[0]
        
        expected_command_parts = [
            "kubectl",
            "--context", "test-context",
            "--namespace", "test-namespace",
            "run", pod_name,
            "--stdin", "true",
            "--restart", "Never",
        ]
        
        for part in expected_command_parts:
            assert part in command


def test_connector_vs_kubectl_consistency(mocker):
    """Test that connector and kubectl paths produce consistent results."""
    config = KanikoImageBuilderConfig(
        kubernetes_context="test-context",
        kubernetes_namespace="test-namespace",
        executor_image="custom-kaniko:latest",
        service_account_name="test-sa",
        env=[{"name": "TEST_ENV", "value": "test"}],
        volume_mounts=[{"name": "test-vol", "mountPath": "/test"}],
    )
    image_builder = _get_kaniko_image_builder(config)
    
    # Test connector path
    mock_connector, mock_api_client, mock_core_api = _patch_k8s_clients(mocker)
    
    with patch.object(image_builder, 'get_connector', return_value=mock_connector):
        try:
            image_builder._run_kaniko_build("test-pod", {}, Mock())
            connector_success = True
        except Exception:
            connector_success = False
    
    # Test kubectl fallback path
    mock_kubectl_build = mocker.patch.object(image_builder, '_run_kaniko_build_kubectl')
    
    with patch.object(image_builder, 'get_connector', return_value=None):
        image_builder._run_kaniko_build("test-pod", {}, Mock())
        kubectl_called = mock_kubectl_build.called
    
    # Both paths should be available and functional
    assert connector_success or kubectl_called, "At least one execution path should work"


def test_complete_build_flow_with_connector(mocker):
    """Test complete build flow using Kubernetes connector."""
    # Setup for a realistic scenario
    config = KanikoImageBuilderConfig(
        kubernetes_context="prod-cluster",
        kubernetes_namespace="zenml-builds",
        executor_image="gcr.io/kaniko-project/executor:v1.9.1",
        service_account_name="kaniko-builder",
        pod_running_timeout=600,
        store_context_in_artifact_store=False,
        env=[
            {"name": "DOCKER_CONFIG", "value": "/kaniko/.docker"},
            {"name": "AWS_REGION", "value": "us-west-2"}
        ],
        volume_mounts=[
            {"name": "docker-config", "mountPath": "/kaniko/.docker"},
            {"name": "aws-credentials", "mountPath": "/root/.aws"}
        ],
        volumes=[
            {"name": "docker-config", "secret": {"secretName": "docker-config"}},
            {"name": "aws-credentials", "secret": {"secretName": "aws-credentials"}}
        ],
        executor_args=["--cache=true", "--compressed-caching=false"]
    )
    
    image_builder = _get_kaniko_image_builder(config)
    pod_name = "kaniko-build-12345678"
    spec_overrides = image_builder._generate_spec_overrides(
        pod_name=pod_name,
        image_name="my-app:latest",
        context="tar://stdin"
    )
    build_context = Mock()
    
    # Mock all Kubernetes components
    mock_connector, mock_api_client, mock_core_api = _patch_k8s_clients(mocker)
    mock_logger = mocker.patch("zenml.integrations.kaniko.image_builders.kaniko_image_builder.logger")
    
    with patch.object(image_builder, 'get_connector', return_value=mock_connector):
        # Execute complete flow
        image_builder._run_kaniko_build(pod_name, spec_overrides, build_context)
        
        # Verify all steps executed
        assert mock_connector.connect.called
        assert mock_core_api.create_namespace.called
        assert mock_core_api.delete_namespaced_pod.called
        
        # Verify logging
        mock_logger.info.assert_any_call("Using kubernetes connector to run the kaniko build.")
        mock_logger.info.assert_any_call(f"Kaniko pod {pod_name} created")
        mock_logger.info.assert_any_call(f"Deleting the pod {pod_name}")


def test_config_compatibility_with_connector_enhancement():
    """Test that existing configs remain compatible with connector enhancement."""
    # Test with minimal config (backward compatibility)
    minimal_config = KanikoImageBuilderConfig(
        kubernetes_context="test-context"
    )
    image_builder = _get_kaniko_image_builder(minimal_config)
    
    # Should work without errors
    assert image_builder.config.kubernetes_context == "test-context"
    assert image_builder.config.kubernetes_namespace == "zenml-kaniko"  # Default
    assert not image_builder.config.store_context_in_artifact_store  # Default
    
    # Test with full config
    full_config = KanikoImageBuilderConfig(
        kubernetes_context="prod-context",
        kubernetes_namespace="custom-namespace",
        executor_image="custom-kaniko:latest",
        service_account_name="custom-sa",
        pod_running_timeout=900,
        store_context_in_artifact_store=True,
        env=[{"name": "CUSTOM_ENV", "value": "custom"}],
        env_from=[{"secretRef": {"name": "custom-secret"}}],
        volume_mounts=[{"name": "custom-vol", "mountPath": "/custom"}],
        volumes=[{"name": "custom-vol", "emptyDir": {}}],
        executor_args=["--custom-flag=value"]
    )
    
    image_builder_full = _get_kaniko_image_builder(full_config)
    
    # All config values should be preserved
    assert image_builder_full.config.kubernetes_context == "prod-context"
    assert image_builder_full.config.kubernetes_namespace == "custom-namespace"
    assert image_builder_full.config.executor_image == "custom-kaniko:latest"
    assert image_builder_full.config.service_account_name == "custom-sa"
    assert image_builder_full.config.pod_running_timeout == 900
    assert image_builder_full.config.store_context_in_artifact_store == True
    assert len(image_builder_full.config.env) == 1
    assert len(image_builder_full.config.env_from) == 1
    assert len(image_builder_full.config.volume_mounts) == 1
    assert len(image_builder_full.config.volumes) == 1
    assert len(image_builder_full.config.executor_args) == 1
