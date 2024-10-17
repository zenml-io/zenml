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
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack

if TYPE_CHECKING:
    from zenml.integrations.skypilot.orchestrators import (
        SkypilotBaseOrchestrator,
    )


def _get_skypilot_orchestrator(
    provider, **kwargs
) -> "SkypilotBaseOrchestrator":
    """Helper function to get a SkyPilot VM orchestrator."""
    from zenml.integrations.skypilot.flavors import (
        SkypilotAWSOrchestratorConfig,
        SkypilotAzureOrchestratorConfig,
        SkypilotGCPOrchestratorConfig,
    )
    from zenml.integrations.skypilot.orchestrators import (
        SkypilotAWSOrchestrator,
        SkypilotAzureOrchestrator,
        SkypilotGCPOrchestrator,
    )

    # Mapping of providers to orchestrator classes and flavors
    orchestrator_map = {
        "aws": (
            SkypilotAWSOrchestrator,
            SkypilotAWSOrchestratorConfig,
            "vm_aws",
        ),
        "azure": (
            SkypilotAzureOrchestrator,
            SkypilotAzureOrchestratorConfig,
            "vm_azure",
        ),
        "gcp": (
            SkypilotGCPOrchestrator,
            SkypilotGCPOrchestratorConfig,
            "vm_gcp",
        ),
    }

    # Get the orchestrator class and flavor based on the provider
    (
        selected_orchestrator_class,
        selected_config_class,
        selected_flavor,
    ) = orchestrator_map.get(provider)

    return selected_orchestrator_class(
        name="",
        id=uuid4(),
        config=selected_config_class(**kwargs),
        flavor=selected_flavor,
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.mark.skip(
    reason="SkyPilot can not be installed in Python 3.9",
)
@pytest.mark.parametrize("provider", ["aws", "azure", "gcp"])
def test_skypilot_orchestrator_local_stack(
    provider,
    local_artifact_store,
    s3_artifact_store,
    remote_container_registry,
) -> None:
    """Test the SkyPilot VM orchestrator with remote stacks."""

    # Test missing container registry
    orchestrator = _get_skypilot_orchestrator(provider)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()
