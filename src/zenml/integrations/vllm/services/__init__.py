#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Initialization of the vLLM Inference Server."""

from zenml.integrations.vllm.services.vllm_deployment import (  # noqa
    VLLMDeploymentService,
    VLLMEngineArgs,
    VLLMServiceConfig,
)

__all__ = [
    "VLLMDeploymentService",
    "VLLMEngineArgs",
    "VLLMServiceConfig",
]

# The Kubernetes vLLM deployment service depends on the `kubernetes`
# package. Guard the import so that the local vLLM deployment service keeps
# working in environments where `kubernetes` is not installed.
try:
    from zenml.integrations.vllm.services.vllm_kubernetes_deployment import (  # noqa
        VLLMKubernetesDeploymentService,
        VLLMKubernetesServiceConfig,
    )

    __all__.extend(
        ["VLLMKubernetesDeploymentService", "VLLMKubernetesServiceConfig"]
    )
except ImportError:
    pass
