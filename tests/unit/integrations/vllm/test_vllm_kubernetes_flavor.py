#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for the vLLM Kubernetes model deployer flavor."""

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.enums import KubernetesServiceType
from zenml.integrations.vllm.flavors.vllm_kubernetes_model_deployer_flavor import (
    KubernetesVLLMModelDeployerConfig,
    KubernetesVLLMModelDeployerFlavor,
)
from zenml.integrations.vllm.model_deployers.vllm_kubernetes_model_deployer import (
    KubernetesVLLMModelDeployer,
)


def test_flavor_name():
    """The flavor name is vllm-kubernetes."""
    flavor = KubernetesVLLMModelDeployerFlavor()
    assert flavor.name == "vllm-kubernetes"


def test_flavor_config_and_implementation_classes():
    """The flavor exposes the Kubernetes vLLM config and deployer classes."""
    flavor = KubernetesVLLMModelDeployerFlavor()
    assert flavor.config_class is KubernetesVLLMModelDeployerConfig
    assert flavor.implementation_class is KubernetesVLLMModelDeployer


def test_flavor_service_connector_requirements_target_kubernetes_cluster():
    """The flavor requires a kubernetes-cluster service connector resource."""
    flavor = KubernetesVLLMModelDeployerFlavor()
    requirements = flavor.service_connector_requirements

    assert requirements is not None
    assert requirements.resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE


def test_config_defaults():
    """The config defaults match the documented Kubernetes vLLM defaults."""
    config = KubernetesVLLMModelDeployerConfig()

    assert config.kubernetes_namespace == "zenml-vllm"
    assert config.default_image == "vllm/vllm-openai:v0.25.1"
    assert config.incluster is False
    assert config.default_service_type == KubernetesServiceType.LOAD_BALANCER
    assert config.kubernetes_context is None
    assert config.hf_token is None


def test_config_is_not_local():
    """The Kubernetes vLLM deployer is not a local stack component."""
    config = KubernetesVLLMModelDeployerConfig()
    assert config.is_local is False
