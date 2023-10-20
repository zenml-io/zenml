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

import pytest
from pydantic import ValidationError

from zenml.config.pipeline_configurations import (
    PipelineConfiguration,
)
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel


def test_pipeline_deployment_base_model_fails_with_long_name():
    """Test that the pipeline deployment base model fails with long names."""
    long_text = "a" * (MEDIUMTEXT_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        PipelineDeploymentBaseModel(
            name="",
            run_name_template="",
            pipeline_configuration=PipelineConfiguration(name="aria_best_cat"),
            step_configurations={"some_key": long_text},
            client_environment={},
        )
