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
"""Utility functions for ZenML entrypoints."""
from typing import TYPE_CHECKING, Type

from zenml.steps import BaseStep
from zenml.steps import utils as step_utils
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step


def load_and_configure_step(step: "Step") -> "BaseStep":
    """Loads and configures a step.

    Additionally, this function creates the executor class necessary for
    this step to be executed.

    Args:
        step: The representation of the step to be loaded.

    Returns:
        The configured step instance.
    """
    step_class: Type[BaseStep] = source_utils.load_and_validate_class(
        step.spec.source, expected_class=BaseStep
    )

    step_instance = step_class()
    step_instance._configuration = step.config
    step_utils.create_executor_class(step=step_instance)

    return step_instance
