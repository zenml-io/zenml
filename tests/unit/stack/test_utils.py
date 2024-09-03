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

from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.enums import StackComponentType
from zenml.orchestrators.local_docker.local_docker_orchestrator import (
    LocalDockerOrchestratorConfig,
)
from zenml.stack.utils import validate_stack_component_config


def test_stack_component_validation_prevents_extras():
    """Tests that stack component validation prevents extra attributes."""
    config_dict = {"not_a_valid_component_attribute": False}

    with does_not_raise():
        LocalDockerOrchestratorConfig(**config_dict)

    with pytest.raises(ValidationError):
        validate_stack_component_config(
            config_dict,
            flavor_name="local_docker",
            component_type=StackComponentType.ORCHESTRATOR,
        )
