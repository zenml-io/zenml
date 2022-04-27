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
from typing import TYPE_CHECKING, AbstractSet, Callable, Optional, Tuple

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)


class StackValidator:
    """A `StackValidator` is used to validate a stack configuration.

    Each `StackComponent` can provide a `StackValidator` to make sure it is
    compatible with all components of the stack. The `KubeflowOrchestrator`
    for example will always require the stack to have a container registry
    in order to push the docker images that are required to run a pipeline
    in Kubeflow Pipelines.
    """

    def __init__(
        self,
        required_components: Optional[AbstractSet[StackComponentType]] = None,
        custom_validation_function: Optional[
            Callable[["Stack"], Tuple[bool, str]]
        ] = None,
    ):
        """Initializes a `StackValidator` instance.

        Args:
            required_components: Optional set of stack components that must
                exist in the stack.
            custom_validation_function: Optional function that returns whether
                a stack is valid and an error message to show if not valid.
        """
        self._required_components = required_components or set()
        self._custom_validation_function = custom_validation_function

    def validate(self, stack: "Stack") -> None:
        """Validates the given stack.

        Checks if the stack contains all the required components and passes
        the custom validation function of the validator.

        Raises:
            StackValidationError: If the stack does not meet all the
                validation criteria.
        """
        missing_components = self._required_components - set(stack.components)
        if missing_components:
            raise StackValidationError(
                f"Missing stack components {missing_components} for "
                f"stack: {stack.name}"
            )

        if self._custom_validation_function:
            valid, err_msg = self._custom_validation_function(stack)
            if not valid:
                raise StackValidationError(
                    f"Custom validation function failed to validate "
                    f"stack '{stack.name}': {err_msg}"
                )
