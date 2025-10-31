#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Dynamic pipeline execution outputs."""

from concurrent.futures import Future
from typing import (
    TYPE_CHECKING,
    Any,
    Tuple,
    Union,
)

from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
)


logger = get_logger(__name__)


class OutputArtifact(ArtifactVersionResponse):
    """Dynamic step run output artifact."""

    output_name: str
    step_name: str


StepRunOutputs = Union[
    None, OutputArtifact, Tuple[OutputArtifact, ...]
]


# TODO: maybe one future per artifact? But for a step that doesn't return anything, the user wouldn't have a future to wait for.
# Or that step returns a future that returns None? Would be similar to a python function.
class StepRunOutputsFuture:
    """Future for a step run output."""

    def __init__(
        self, wrapped: Future[StepRunOutputs], invocation_id: str
    ) -> None:
        """Initialize the future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
        """
        self._wrapped = wrapped
        self._invocation_id = invocation_id

    def wait(self) -> None:
        """Wait for the future to complete."""
        self._wrapped.result()

    def result(self) -> StepRunOutputs:
        """Get the step run output artifacts.

        Returns:
            The step run output artifacts.
        """
        return self._wrapped.result()

    def load(self) -> Any:
        """Get the step run output artifact data.

        Raises:
            ValueError: If the step run output is invalid.

        Returns:
            The step run output artifact data.
        """
        result = self.result()

        if result is None:
            return None
        elif isinstance(result, ArtifactVersionResponse):
            return result.load()
        elif isinstance(result, tuple):
            return tuple(item.load() for item in result)
        else:
            raise ValueError(f"Invalid step run output: {result}")
