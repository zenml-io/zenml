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
"""Initialization of the Skypilot ZenML orchestrators."""

from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (  # noqa
    SkypilotBaseOrchestrator,
)
from zenml.integrations.skypilot.orchestrators.skypilot_aws_vm_orchestrator import (  # noqa
    SkypilotAWSOrchestrator,
)
from zenml.integrations.skypilot.orchestrators.skypilot_gcp_vm_orchestrator import (  # noqa
    SkypilotGCPOrchestrator,
)
from zenml.integrations.skypilot.orchestrators.skypilot_azure_vm_orchestrator import (  # noqa
    SkypilotAzureOrchestrator,
)

__all__ = [
    "SkypilotBaseOrchestrator",
    "SkypilotAWSOrchestrator",
    "SkypilotGCPOrchestrator",
    "SkypilotAzureOrchestrator",
]
