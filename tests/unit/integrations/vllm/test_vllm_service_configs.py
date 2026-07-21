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
"""Unit tests for the vLLM service configs.

`VLLMEngineArgs` was extracted as a shared mixin for the local
`VLLMServiceConfig` and the Kubernetes `VLLMKubernetesServiceConfig`. These
tests pin down the field defaults on both configs so the extraction did not
change either one's behavior.
"""

from zenml.integrations.vllm.services.vllm_deployment import VLLMServiceConfig
from zenml.integrations.vllm.services.vllm_kubernetes_deployment import (
    VLLMKubernetesServiceConfig,
)


def test_local_service_config_engine_defaults():
    """VLLMServiceConfig keeps its engine field defaults after the mixin extraction."""
    config = VLLMServiceConfig(
        name="vllm-test", model="facebook/opt-125m", port=8000
    )

    assert config.model == "facebook/opt-125m"
    assert config.tokenizer is None
    assert config.served_model_name is None
    assert config.trust_remote_code is False
    assert config.tokenizer_mode == "auto"
    assert config.dtype == "auto"
    assert config.revision is None


def test_local_service_config_service_defaults():
    """VLLMServiceConfig keeps its own non-engine field defaults."""
    config = VLLMServiceConfig(
        name="vllm-test", model="facebook/opt-125m", port=8000
    )

    assert config.port == 8000
    assert config.host is None
    assert config.blocking is True


def test_kubernetes_service_config_engine_defaults():
    """VLLMKubernetesServiceConfig inherits the same engine field defaults."""
    config = VLLMKubernetesServiceConfig(
        name="vllm-test", model="facebook/opt-125m"
    )

    assert config.model == "facebook/opt-125m"
    assert config.tokenizer is None
    assert config.served_model_name is None
    assert config.trust_remote_code is False
    assert config.tokenizer_mode == "auto"
    assert config.dtype == "auto"
    assert config.revision is None


def test_kubernetes_service_config_defaults():
    """VLLMKubernetesServiceConfig field defaults match the plan."""
    config = VLLMKubernetesServiceConfig(
        name="vllm-test", model="facebook/opt-125m"
    )

    assert config.port == 8000
    assert config.replicas == 1
    assert config.shm_size == "2Gi"
    assert config.namespace is None
    assert config.image is None
    assert config.service_type is None
    assert config.resources == {}
    assert config.pod_settings is None
    assert config.hf_token is None
    assert config.existing_hf_secret is None
    assert config.env == {}
    assert config.extra_serve_args == []
