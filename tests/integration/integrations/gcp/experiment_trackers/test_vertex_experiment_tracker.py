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

import re
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest
from mock import MagicMock

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
    """Returns a Vertex experiment tracker."""
    return VertexExperimentTracker(
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

def is_valid_experiment_name(name: str) -> bool:
    """Check if the experiment name matches the required regex."""
    EXPERIMENT_NAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
    return bool(EXPERIMENT_NAME_REGEX.match(name))


@pytest.mark.parametrize("input_name,expected_output", [
    ("My Experiment Name", "my-experiment-name"),
    ("My_Experiment_Name", "my-experiment-name"),
    ("MyExperimentName123", "myexperimentname123"),
    ("Name-With-Dashes---", "name-with-dashes"),
    ("Invalid!Name", "invalid-name"),
    ("   Whitespace Name  ", "whitespace-name"),
    ("UPPERCASE", "uppercase"),
    ("a" * 140, "a" * 128),  # Truncated to 128 chars
    ("special&%_characters", "special---characters"),
])
def test_format_name(vertex_experiment_tracker, input_name, expected_output):
    """Test the name formatting function."""
    formatted_name = vertex_experiment_tracker._format_name(input_name)
    assert formatted_name == expected_output, f"Failed for input: '{input_name}'"
    assert is_valid_experiment_name(formatted_name), f"Formatted name '{formatted_name}' does not match the regex"


@pytest.mark.parametrize("input_name,expected_output", [
    ("My Experiment", "my-experiment"),
    ("Another Experiment", "another-experiment"),
    (None, "default-experiment"),
    ("", "default-experiment"),
])
def test_get_experiment_name(vertex_experiment_tracker, input_name, expected_output):
    """Test the experiment name generation function."""
    mock_settings = MagicMock()
    mock_settings.experiment = input_name
    vertex_experiment_tracker.get_settings = MagicMock(return_value=mock_settings)

    info = MagicMock()
    info.pipeline.name = "default-experiment"

    experiment_name = vertex_experiment_tracker._get_experiment_name(info)
    assert experiment_name == expected_output, f"Failed for input: '{input_name}'"
    assert is_valid_experiment_name(experiment_name), f"Generated experiment name '{experiment_name}' does not match the regex"


@pytest.mark.parametrize("input_name,expected_output", [
    ("Run-001", "run-001"),
    ("AnotherRun", "anotherrun"),
    ("run_with_special_chars!@#", "run-with-special-chars"),
])
def test_get_run_name(vertex_experiment_tracker, input_name, expected_output):
    """Test the run name generation function."""
    info = MagicMock()
    info.run_name = input_name

    run_name = vertex_experiment_tracker._get_run_name(info)
    assert run_name == expected_output, f"Failed for input: '{input_name}'"
    assert is_valid_experiment_name(run_name), f"Generated run name '{run_name}' does not match the regex"
