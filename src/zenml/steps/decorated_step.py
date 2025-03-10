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

from __future__ import annotations

from typing import Any, TypeVar

from typing_extensions import ParamSpec

from zenml.config.source import Source
from zenml.steps import BaseStep

P = ParamSpec("P")
R = TypeVar("R")


class _DecoratedStep(BaseStep[P, R]):
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

        return source_utils.resolve(self.entrypoint, skip_validation=True)
