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

from zenml.artifact_stores import LocalArtifactStore, LocalArtifactStoreConfig
from zenml.enums import StackComponentType
from zenml.integrations.neptune.experiment_trackers import (
    NeptuneExperimentTracker,
)
from zenml.integrations.neptune.flavors import NeptuneExperimentTrackerConfig
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack
from zenml.stack.stack_component import StackComponentConfig


@pytest.fixture(scope="session")
def neptune_experiment_tracker() -> NeptuneExperimentTracker:
    yield NeptuneExperimentTracker(
        name="",
        id=uuid4(),
        config=NeptuneExperimentTrackerConfig(
            project="example-project",
            api_token="ANONYMOUS",
        ),
        flavor="neptune",
        type=StackComponentType.EXPERIMENT_TRACKER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture(scope="session")
def local_orchestrator() -> LocalOrchestrator:
    yield LocalOrchestrator(
        name="",
        id=uuid4(),
        config=StackComponentConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture(scope="session")
def local_artifact_store() -> LocalArtifactStore:
    yield LocalArtifactStore(
        name="",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_neptune_experiment_tracker_attributes(
    neptune_experiment_tracker,
) -> None:
    """Tests that the basic attributes of the neptune experiment tracker are set correctly."""
    assert (
        neptune_experiment_tracker.type
        == StackComponentType.EXPERIMENT_TRACKER
    )
    assert neptune_experiment_tracker.flavor == "neptune"


def test_neptune_experiment_tracker_stack_validation(
    neptune_experiment_tracker,
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
            experiment_tracker=neptune_experiment_tracker,
        ).validate()


def test_neptune_experiment_tracker_does_not_need_explicit_api_token_or_project() -> (
    None
):
    """Test that passing an empty config upon constructing neptune experiment tracker still works
    (arguments are optional).
    """
    with does_not_raise():
        NeptuneExperimentTracker(
            name="",
            id=uuid4(),
            config=NeptuneExperimentTrackerConfig(),
            flavor="neptune",
            type=StackComponentType.EXPERIMENT_TRACKER,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )
