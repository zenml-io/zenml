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
from typing import Any, List, Tuple, Union

from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
)

logger = get_logger(__name__)


class OutputArtifact(ArtifactVersionResponse):
    """Dynamic step run output artifact."""

    output_name: str
    step_name: str


StepRunOutputs = Union[None, OutputArtifact, Tuple[OutputArtifact, ...]]


class ArtifactFuture:
    """Future for a step run output artifact."""

    def __init__(
        self, wrapped: Future[StepRunOutputs], invocation_id: str, index: int
    ) -> None:
        """Initialize the future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
        """
        self._wrapped = wrapped
        self._invocation_id = invocation_id
        self._index = index

    def _wait(self) -> None:
        self._wrapped.result()

    def result(self) -> OutputArtifact:
        """Get the step run output artifact.

        Returns:
            The step run output artifact.
        """
        result = self._wrapped.result()
        if isinstance(result, OutputArtifact):
            return result
        elif isinstance(result, tuple):
            return result[self._index]
        else:
            raise RuntimeError(
                f"Step {self._invocation_id} returned an invalid output: {result}"
            )

    def load(self) -> Any:
        """Load the step run output artifact data.

        Returns:
            The step run output artifact data.
        """
        return self.result().load()


class StepRunOutputsFuture:
    """Future for a step run output."""

    def __init__(
        self,
        wrapped: Future[StepRunOutputs],
        invocation_id: str,
        output_keys: List[str],
    ) -> None:
        """Initialize the future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
        """
        self._wrapped = wrapped
        self._invocation_id = invocation_id
        self._output_keys = output_keys

    def _wait(self) -> None:
        self._wrapped.result()

    def artifacts(self) -> StepRunOutputs:
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
        result = self.artifacts()

        if result is None:
            return None
        elif isinstance(result, ArtifactVersionResponse):
            return result.load()
        elif isinstance(result, tuple):
            return tuple(item.load() for item in result)
        else:
            raise ValueError(f"Invalid step run output: {result}")

    def __getitem__(self, key: Union[str, int]) -> ArtifactFuture:
        if isinstance(key, str):
            index = self._output_keys.index(key)
        elif isinstance(key, int):
            index = key
        else:
            raise ValueError(f"Invalid key type: {type(key)}")

        if index > len(self._output_keys):
            raise IndexError(f"Index out of range: {index}")

        return ArtifactFuture(
            wrapped=self._wrapped,
            invocation_id=self._invocation_id,
            index=index,
        )

    def __iter__(self) -> Any:
        if not self._output_keys:
            raise ValueError(
                f"Step {self._invocation_id} does not return any outputs."
            )

        for index in range(len(self._output_keys)):
            yield ArtifactFuture(
                wrapped=self._wrapped,
                invocation_id=self._invocation_id,
                index=index,
            )

    def __len__(self) -> int:
        return len(self._output_keys)


StepRunFuture = Union[ArtifactFuture, StepRunOutputsFuture]
