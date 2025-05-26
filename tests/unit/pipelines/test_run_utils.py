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
    """Test that create_placeholder_run passes through improved error message from zen_store."""
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

    # Mock the client and zen_store to raise EntityExistsError with improved message
    improved_error_message = (
        "Pipeline run name 'my_test_run' already exists in this project. "
        "Each pipeline run must have a unique name.\n\n"
        "To fix this, you can:\n"
        "1. Use a different run name\n"
        '2. Use a dynamic run name with placeholders like: "my_test_run_{date}_{time}"\n'
        "3. Remove the run name from your configuration to auto-generate unique names\n\n"
        "For more information on run naming, see: https://docs.zenml.io/concepts/steps_and_pipelines/yaml_configuration#run-name"
    )
    mock_client.return_value.zen_store.get_or_create_run.side_effect = (
        EntityExistsError(improved_error_message)
    )

    # Test that the error from zen_store is passed through unchanged
    with pytest.raises(EntityExistsError) as exc_info:
        run_utils.create_placeholder_run(deployment)

    error_message = str(exc_info.value)

    # Verify the error message is exactly what zen_store raised
    assert error_message == improved_error_message
