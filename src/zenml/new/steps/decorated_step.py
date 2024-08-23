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
"""Internal BaseStep subclass used by the step decorator."""

from typing import Any

from zenml.config.source import Source
from zenml.constants import (
    STEP_DECO_DECORATOR_FUNCTION,
    STEP_DECO_DECORATOR_KWARGS,
)
from zenml.steps import BaseStep


class _DecoratedStep(BaseStep):
    """Internal BaseStep subclass used by the step decorator."""

    @property
    def source_object(self) -> Any:
        """The source object of this step.

        Returns:
            The source object of this step.
        """
        return self.entrypoint

    def resolve(self) -> "Source":
        """Resolves the step.

        Returns:
            The step source.
        """
        from zenml.utils import source_utils

        source = source_utils.resolve(self.entrypoint, skip_validation=True)

        if dynamic_decorator := getattr(
            self, STEP_DECO_DECORATOR_FUNCTION, None
        ):
            dynamic_decorator_source = source_utils.resolve(
                dynamic_decorator, skip_validation=True
            )
            (
                source.dynamic_decorator_module,
                source.dynamic_decorator_attribute,
                source.dynamic_decorator_type,
            ) = (
                dynamic_decorator_source.module,
                dynamic_decorator_source.attribute,
                dynamic_decorator_source.type,
            )
            source.dynamic_decorator_kwargs = getattr(
                self, STEP_DECO_DECORATOR_KWARGS, {}
            )

        return source
