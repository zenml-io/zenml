#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import (
    AirflowOrchestratorConfig,
)
from zenml.integrations.airflow.orchestrators import AirflowOrchestrator


def test_airflow_orchestrator_attributes():
    """Tests that the basic attributes of the airflow orchestrator are set correctly."""
    orchestrator = AirflowOrchestrator(
        name="",
        id=uuid4(),
        config=AirflowOrchestratorConfig(),
        flavor="airflow",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    assert orchestrator.type == StackComponentType.ORCHESTRATOR
    assert orchestrator.flavor == "airflow"
    assert orchestrator.config.local is True


def test_resource_appliciation():
    """Tests applying resources to an airflow task works as expected."""
    orchestrator = AirflowOrchestrator(
        name="",
        id=uuid4(),
        config=AirflowOrchestratorConfig(),
        flavor="airflow",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    operator_args = {}

    resource_settings = ResourceSettings(
        cpu_count=2, gpu_count=3, memory="10GB"
    )

    orchestrator._apply_resource_settings(
        resource_settings, operator_args=operator_args
    )
    limits = operator_args["container_resources"]["limits"]
    assert limits["cpu"] == "2.0"
    assert limits["memory"] == "10G"
    assert len(limits) == 2  # GPU not in there

    operator_args = {"container_resources": "dummy_resources"}
    orchestrator._apply_resource_settings(
        resource_settings, operator_args=operator_args
    )
    # Resource settings get ignored when user specified custom container
    # resources
    assert operator_args == {"container_resources": "dummy_resources"}
