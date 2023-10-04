#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Skypilot integration flavors."""

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_aws_vm_flavor import (
    SkypilotAWSOrchestratorConfig,
    SkypilotAWSOrchestratorFlavor,
    SkypilotAWSOrchestratorSettings,
)
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_gcp_vm_flavor import (
    SkypilotGCPOrchestratorConfig,
    SkypilotGCPOrchestratorFlavor,
    SkypilotGCPOrchestratorSettings,
)
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_azure_vm_flavor import (
    SkypilotAzureOrchestratorConfig,
    SkypilotAzureOrchestratorFlavor,
    SkypilotAzureOrchestratorSettings,
)

__all__ = [
    "SkypilotAWSOrchestratorConfig",
    "SkypilotAWSOrchestratorFlavor",
    "SkypilotAWSOrchestratorSettings",
    "SkypilotGCPOrchestratorConfig",
    "SkypilotGCPOrchestratorFlavor",
    "SkypilotGCPOrchestratorSettings",
    "SkypilotAzureOrchestratorConfig",
    "SkypilotAzureOrchestratorFlavor",
    "SkypilotAzureOrchestratorSettings",
]
