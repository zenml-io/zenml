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

from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.integrations.gcp.experiment_trackers.vertex_experiment_tracker import (
    VertexExperimentTracker,
)
from zenml.integrations.gcp.flavors.vertex_experiment_tracker_flavor import (
    VertexExperimentTrackerConfig,
)
from zenml.stack import Stack


@pytest.fixture(scope="session")
def vertex_experiment_tracker() -> VertexExperimentTracker:
    yield VertexExperimentTracker(
        name="",
        id=uuid4(),
        config=VertexExperimentTrackerConfig(),
        flavor="vertex",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_vertex_experiment_tracker_stack_validation(
    vertex_experiment_tracker,
    local_orchestrator,
    local_artifact_store,
) -> None:
    """Tests that a stack with neptune experiment tracker is valid."""
    with does_not_raise():
        Stack(
            name="",
            id=uuid4(),
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            experiment_tracker=vertex_experiment_tracker,
        ).validate()


def test_vertex_experiment_tracker_attributes(
    vertex_experiment_tracker,
) -> None:
    """Tests that the basic attributes of the neptune experiment tracker are set correctly."""
    assert (
        vertex_experiment_tracker.type == StackComponentType.EXPERIMENT_TRACKER
    )
    assert vertex_experiment_tracker.flavor == "vertex"
