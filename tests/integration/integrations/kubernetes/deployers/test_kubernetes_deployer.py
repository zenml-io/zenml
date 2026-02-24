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
"""Tests for the Kubernetes deployer template context building."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerSettings,
)
from zenml.integrations.kubernetes.pod_settings import (
    KubernetesPodSettings,
)


@pytest.fixture
def deployer_instance():
    """Create a KubernetesDeployer instance with mocked config."""
    with patch(
        "zenml.integrations.kubernetes.deployers.kubernetes_deployer.KubernetesDeployer.__init__",
        return_value=None,
    ):
        from zenml.integrations.kubernetes.deployers.kubernetes_deployer import (
            KubernetesDeployer,
        )

        deployer = KubernetesDeployer()
        deployer._k8s_client = None
        deployer._applier = None
        return deployer


@pytest.fixture
def mock_deployment():
    """Create a mock deployment response."""
    deployment = MagicMock()
    deployment.id = str(uuid4())
    deployment.snapshot = MagicMock()
    deployment.snapshot.id = str(uuid4())
    return deployment


class TestBuildTemplateContextResources:
    """Tests for pod_settings.resources merging in _build_template_context."""

    def test_pod_settings_resources_applied_when_no_resource_settings(
        self, deployer_instance, mock_deployment
    ):
        """pod_settings.resources should be used when ResourceSettings are empty."""
        settings = KubernetesDeployerSettings(
            pod_settings=KubernetesPodSettings(
                resources={
                    "requests": {"cpu": "100m", "memory": "400Mi"},
                    "limits": {"cpu": "200m", "memory": "800Mi"},
                }
            )
        )

        context = deployer_instance._build_template_context(
            deployment=mock_deployment,
            settings=settings,
            resource_name="test-deployment",
            namespace="zenml",
            labels={"app": "test"},
            image="test:latest",
            env_vars={},
            secret_env_vars={},
            secret_name="test-secret",
            resource_requests={},
            resource_limits={},
            replicas=1,
        )

        assert context["resources"] is not None
        assert context["resources"]["requests"]["cpu"] == "100m"
        assert context["resources"]["requests"]["memory"] == "400Mi"
        assert context["resources"]["limits"]["cpu"] == "200m"
        assert context["resources"]["limits"]["memory"] == "800Mi"

    def test_pod_settings_resources_overrides_resource_settings(
        self, deployer_instance, mock_deployment
    ):
        """pod_settings.resources should take precedence over ResourceSettings."""
        settings = KubernetesDeployerSettings(
            pod_settings=KubernetesPodSettings(
                resources={
                    "requests": {"cpu": "500m"},
                    "limits": {"cpu": "1", "memory": "2Gi"},
                }
            )
        )

        context = deployer_instance._build_template_context(
            deployment=mock_deployment,
            settings=settings,
            resource_name="test-deployment",
            namespace="zenml",
            labels={"app": "test"},
            image="test:latest",
            env_vars={},
            secret_env_vars={},
            secret_name="test-secret",
            resource_requests={"cpu": "100m", "memory": "400Mi"},
            resource_limits={},
            replicas=1,
        )

        # pod_settings overrides cpu request, memory request is kept
        assert context["resources"]["requests"]["cpu"] == "500m"
        assert context["resources"]["requests"]["memory"] == "400Mi"
        # limits come entirely from pod_settings
        assert context["resources"]["limits"]["cpu"] == "1"
        assert context["resources"]["limits"]["memory"] == "2Gi"

    def test_no_resources_when_nothing_specified(
        self, deployer_instance, mock_deployment
    ):
        """resources should be None when neither source provides values."""
        settings = KubernetesDeployerSettings()

        context = deployer_instance._build_template_context(
            deployment=mock_deployment,
            settings=settings,
            resource_name="test-deployment",
            namespace="zenml",
            labels={"app": "test"},
            image="test:latest",
            env_vars={},
            secret_env_vars={},
            secret_name="test-secret",
            resource_requests={},
            resource_limits={},
            replicas=1,
        )

        assert context["resources"] is None

    def test_only_resource_settings_still_works(
        self, deployer_instance, mock_deployment
    ):
        """ResourceSettings alone (no pod_settings) should still work."""
        settings = KubernetesDeployerSettings()

        context = deployer_instance._build_template_context(
            deployment=mock_deployment,
            settings=settings,
            resource_name="test-deployment",
            namespace="zenml",
            labels={"app": "test"},
            image="test:latest",
            env_vars={},
            secret_env_vars={},
            secret_name="test-secret",
            resource_requests={"cpu": "100m", "memory": "256Mi"},
            resource_limits={"nvidia.com/gpu": "1"},
            replicas=1,
        )

        assert context["resources"]["requests"]["cpu"] == "100m"
        assert context["resources"]["requests"]["memory"] == "256Mi"
        assert context["resources"]["limits"]["nvidia.com/gpu"] == "1"

    def test_pod_settings_limits_only(
        self, deployer_instance, mock_deployment
    ):
        """pod_settings with only limits (no requests) should work."""
        settings = KubernetesDeployerSettings(
            pod_settings=KubernetesPodSettings(
                resources={
                    "limits": {"cpu": "200m", "memory": "800Mi"},
                }
            )
        )

        context = deployer_instance._build_template_context(
            deployment=mock_deployment,
            settings=settings,
            resource_name="test-deployment",
            namespace="zenml",
            labels={"app": "test"},
            image="test:latest",
            env_vars={},
            secret_env_vars={},
            secret_name="test-secret",
            resource_requests={},
            resource_limits={},
            replicas=1,
        )

        assert context["resources"] is not None
        assert "requests" not in context["resources"]
        assert context["resources"]["limits"]["cpu"] == "200m"
        assert context["resources"]["limits"]["memory"] == "800Mi"
