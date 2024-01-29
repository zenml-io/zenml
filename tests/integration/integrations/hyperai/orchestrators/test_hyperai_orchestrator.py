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
from datetime import datetime
from uuid import uuid4

from zenml.config import ResourceSettings
from zenml.enums import StackComponentType
from zenml.integrations.hyperai.orchestrators.hyperai_orchestrator import HyperAIOrchestrator
from zenml.integrations.hyperai.orchestrators.hyperai_orchestrator  import (
    HyperAIOrchestratorConfig,
)


def test_hyperai_orchestrator_attributes():
    """Tests that the basic attributes of the HyperAI orchestrator are set correctly."""
    orchestrator = HyperAIOrchestrator(
        name="",
        id=uuid4(),
        config=HyperAIOrchestratorConfig(),
        flavor="hyperai",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    assert orchestrator.type == StackComponentType.ORCHESTRATOR
    assert orchestrator.flavor == "hyperai"
    assert orchestrator.config.remote is True
    assert orchestrator.config.container_registry_autologin is False