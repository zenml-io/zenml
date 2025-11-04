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
"""Shared fixtures for Kubernetes integration unit tests."""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock

import pytest
from kubernetes import client as k8s_client


@pytest.fixture
def mock_k8s_api_client() -> MagicMock:
    """Create a mock Kubernetes API client for testing."""
    mock_client = MagicMock(spec=k8s_client.ApiClient)
    mock_client.configuration = MagicMock()
    mock_client.configuration.host = "https://kubernetes.default.svc"
    return mock_client


@pytest.fixture
def mock_dynamic_client(mock_k8s_api_client: MagicMock) -> MagicMock:
    """Create a mock Kubernetes dynamic client with resource API."""
    from kubernetes.dynamic import DynamicClient

    mock_client = MagicMock(spec=DynamicClient)
    mock_client.client = mock_k8s_api_client

    # Mock the resource API structure
    def mock_resource_getter(api_version: str, kind: str) -> Mock:
        mock_resource = Mock()
        mock_resource.kind = kind
        mock_resource.api_version = api_version
        mock_resource.namespaced = kind not in [
            "Namespace",
            "ClusterRole",
            "ClusterRoleBinding",
            "CustomResourceDefinition",
        ]

        # Mock server-side apply
        def mock_patch(*args: Any, **kwargs: Any) -> Mock:
            resource_obj = Mock()
            resource_obj.metadata = Mock()
            resource_obj.metadata.name = kwargs.get("name", "test-resource")
            resource_obj.metadata.namespace = kwargs.get("namespace")
            return resource_obj

        mock_resource.patch = Mock(side_effect=mock_patch)
        mock_resource.get = Mock()
        mock_resource.delete = Mock()

        return mock_resource

    mock_client.resources.get = Mock(side_effect=mock_resource_getter)
    return mock_client


@pytest.fixture
def sample_deployment_manifest() -> Dict[str, Any]:
    """Sample Kubernetes Deployment manifest for testing."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "test-deployment",
            "namespace": "test-namespace",
            "labels": {
                "app": "test-app",
                "managed-by": "zenml",
            },
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "test-app",
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "test-app",
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "main",
                            "image": "test-image:latest",
                            "ports": [{"containerPort": 8000}],
                        }
                    ]
                },
            },
        },
    }


@pytest.fixture
def sample_service_manifest() -> Dict[str, Any]:
    """Sample Kubernetes Service manifest for testing."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "test-service",
            "namespace": "test-namespace",
            "labels": {
                "app": "test-app",
                "managed-by": "zenml",
            },
        },
        "spec": {
            "type": "LoadBalancer",
            "selector": {
                "app": "test-app",
            },
            "ports": [
                {
                    "port": 8000,
                    "targetPort": 8000,
                    "protocol": "TCP",
                    "name": "http",
                }
            ],
        },
    }


@pytest.fixture
def sample_namespace_manifest() -> Dict[str, Any]:
    """Sample Kubernetes Namespace manifest for testing."""
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": "test-namespace",
            "labels": {
                "managed-by": "zenml",
            },
        },
    }


@pytest.fixture
def sample_template_context() -> Dict[str, Any]:
    """Sample template context for rendering Kubernetes manifests."""
    return {
        "name": "test-deployment",
        "namespace": "test-namespace",
        "image": "zenml/test-image:latest",
        "replicas": 2,
        "labels": {
            "app": "test-app",
            "zenml-deployment-id": "12345",
            "zenml-deployment-name": "test-deployment",
        },
        "annotations": {},
        "service_account_name": None,
        "image_pull_policy": "IfNotPresent",
        "image_pull_secrets": [],
        "command": None,
        "args": None,
        "env": {
            "ENV_VAR_1": "value1",
            "ENV_VAR_2": "value2",
        },
        "resources": {
            "requests": {
                "cpu": "100m",
                "memory": "256Mi",
            },
            "limits": {
                "cpu": "500m",
                "memory": "512Mi",
            },
        },
        "pod_settings": None,
        "security_context": None,
        "service_type": "LoadBalancer",
        "service_port": 8000,
        "target_port": 8000,
        "readiness_probe_path": "/api/health",
        "readiness_probe_initial_delay": 15,
        "readiness_probe_period": 10,
        "readiness_probe_timeout": 5,
        "readiness_probe_failure_threshold": 3,
        "liveness_probe_path": "/api/health",
        "liveness_probe_initial_delay": 30,
        "liveness_probe_period": 20,
        "liveness_probe_timeout": 5,
        "liveness_probe_failure_threshold": 3,
        "probe_port": 8000,
    }


@pytest.fixture
def temp_templates_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for custom templates."""
    templates_dir = tmp_path / "custom_templates"
    templates_dir.mkdir(parents=True)
    return templates_dir


@pytest.fixture
def custom_deployment_template(temp_templates_dir: Path) -> Path:
    """Create a custom deployment template for testing."""
    template_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ name | k8s_name }}
  namespace: {{ namespace }}
  labels:
    custom: "true"
spec:
  replicas: {{ replicas }}
  selector:
    matchLabels:
      app: {{ name | k8s_name }}
  template:
    metadata:
      labels:
        app: {{ name | k8s_name }}
    spec:
      containers:
      - name: main
        image: {{ image }}
        env:
        {% for key, value in env.items() %}
        - name: {{ key }}
          value: {{ value | tojson }}
        {% endfor %}
"""
    template_path = temp_templates_dir / "deployment.yaml.j2"
    template_path.write_text(template_content)
    return template_path


@pytest.fixture
def sample_raw_yaml_manifest(tmp_path: Path) -> Path:
    """Create a sample raw YAML manifest file for testing."""
    yaml_content = """---
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
  namespace: test-namespace
data:
  key1: value1
  key2: value2
---
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  namespace: test-namespace
type: Opaque
data:
  password: cGFzc3dvcmQ=
"""
    manifest_path = tmp_path / "test-manifest.yaml"
    manifest_path.write_text(yaml_content)
    return manifest_path


@pytest.fixture
def mock_deployment_object() -> Mock:
    """Create a mock Kubernetes Deployment object."""
    mock_obj = Mock()
    mock_obj.kind = "Deployment"
    mock_obj.metadata = Mock()
    mock_obj.metadata.name = "test-deployment"
    mock_obj.metadata.namespace = "test-namespace"
    mock_obj.spec = Mock()
    mock_obj.spec.replicas = 1
    mock_obj.status = Mock()
    mock_obj.status.replicas = 1
    mock_obj.status.ready_replicas = 1
    mock_obj.status.updated_replicas = 1
    mock_obj.status.available_replicas = 1

    # Add to_dict method for applier methods that need it
    mock_obj.to_dict = Mock(
        return_value={
            "status": {
                "conditions": [{"type": "Available", "status": "True"}],
                "replicas": 1,
                "ready_replicas": 1,
                "updated_replicas": 1,
                "available_replicas": 1,
            }
        }
    )
    return mock_obj


@pytest.fixture
def mock_service_object() -> Mock:
    """Create a mock Kubernetes Service object."""
    mock_obj = Mock()
    mock_obj.kind = "Service"
    mock_obj.metadata = Mock()
    mock_obj.metadata.name = "test-service"
    mock_obj.metadata.namespace = "test-namespace"
    mock_obj.spec = Mock()
    mock_obj.spec.type = "LoadBalancer"
    mock_obj.status = Mock()
    mock_obj.status.load_balancer = Mock()
    mock_obj.status.load_balancer.ingress = [Mock(ip="10.0.0.1")]

    # Add to_dict method for applier methods that need it
    mock_obj.to_dict = Mock(
        return_value={
            "status": {"loadBalancer": {"ingress": [{"ip": "10.0.0.1"}]}}
        }
    )
    return mock_obj
