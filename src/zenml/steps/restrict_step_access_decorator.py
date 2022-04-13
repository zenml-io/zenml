#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Any

from zenml.environment import Environment
from zenml.exceptions import ForbiddenRepositoryAccessError
from zenml.logger import get_logger

logger = get_logger(__name__)


def restrict_step_access(_func: Any) -> Any:
    """Decorator to restrict this function from running inside a step.

    Apply this decorator to a ZenML function to prevent it from being run
    inside the context of a step.

    Args:
        _func: The function to restrict access to, inside a step.

    Returns:
        The same function without any enhancements but checks the Environment
        to see if it's running inside a step.

    Raises:
        ForbiddenRepositoryAccessError: If trying to create a `Repository`
            instance while a ZenML step is being executed.
    """

    if Environment().step_is_running:
        raise ForbiddenRepositoryAccessError(
            "Unable to access repository during step execution. If you "
            "require access to the artifact or metadata store, please use "
            "a `StepContext` inside your step instead.",
            url="https://docs.zenml.io/features/step-fixtures#using-the-stepcontext",
        )

    return _func
