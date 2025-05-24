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
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.exceptions import EntityExistsError
from zenml.models import (
    PipelineDeploymentResponse,
    UserResponse,
)
from zenml.pipelines import run_utils


def test_default_run_name():
    """Tests the default run name value."""
    assert (
        run_utils.get_default_run_name(pipeline_name="my_pipeline")
        == "my_pipeline-{date}-{time}"
    )


@patch("zenml.pipelines.run_utils.Client")
def test_create_placeholder_run_duplicate_name_error(mock_client):
    """Test that create_placeholder_run provides a helpful error message for duplicate run names."""
    # Mock the deployment
    deployment = MagicMock(spec=PipelineDeploymentResponse)
    deployment.user = MagicMock(spec=UserResponse)
    deployment.schedule = None
    deployment.run_name_template = "my_test_run"
    deployment.pipeline_configuration.finalize_substitutions.return_value = {}
    deployment.project.id = uuid4()
    deployment.id = uuid4()
    deployment.pipeline.id = uuid4()
    deployment.pipeline_configuration.tags = []

    # Mock the client and zen_store to raise EntityExistsError
    original_error_message = (
        "Unable to create the requested pipeline run with name 'my_test_run': "
        "Found another existing pipeline run with the same name in the 'test_project' project."
    )
    mock_client.return_value.zen_store.get_or_create_run.side_effect = (
        EntityExistsError(original_error_message)
    )

    # Test that our improved error message is raised
    with pytest.raises(EntityExistsError) as exc_info:
        run_utils.create_placeholder_run(deployment)

    error_message = str(exc_info.value)

    # Verify the improved error message contains helpful guidance
    assert (
        "Pipeline run name 'my_test_run' already exists in this project"
        in error_message
    )
    assert "Each pipeline run must have a unique name" in error_message
    assert "Change the 'run_name' in your config" in error_message
    assert "Use a dynamic run name with placeholders" in error_message
    assert "Remove the 'run_name' from your config" in error_message
    assert (
        "https://docs.zenml.io/concepts/steps_and_pipelines/yaml_configuration#run-name"
        in error_message
    )


@patch("zenml.pipelines.run_utils.Client")
def test_create_placeholder_run_non_duplicate_name_error(mock_client):
    """Test that create_placeholder_run re-raises non-duplicate-name EntityExistsErrors unchanged."""
    # Mock the deployment
    deployment = MagicMock(spec=PipelineDeploymentResponse)
    deployment.user = MagicMock(spec=UserResponse)
    deployment.schedule = None
    deployment.run_name_template = "my_test_run"
    deployment.pipeline_configuration.finalize_substitutions.return_value = {}
    deployment.project.id = uuid4()
    deployment.id = uuid4()
    deployment.pipeline.id = uuid4()
    deployment.pipeline_configuration.tags = []

    # Mock the client and zen_store to raise a different EntityExistsError
    original_error_message = "Some other entity exists error"
    mock_client.return_value.zen_store.get_or_create_run.side_effect = (
        EntityExistsError(original_error_message)
    )

    # Test that the original error message is preserved for non-duplicate-name errors
    with pytest.raises(EntityExistsError) as exc_info:
        run_utils.create_placeholder_run(deployment)

    error_message = str(exc_info.value)

    # Verify the original error message is preserved
    assert error_message == original_error_message
