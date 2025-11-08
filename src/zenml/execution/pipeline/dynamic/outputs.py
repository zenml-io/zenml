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


class _BaseStepRunFuture:
    """Base step run future."""

    def __init__(
        self,
        wrapped: Future[StepRunOutputs],
        invocation_id: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the dynamic step run future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
            **kwargs: Additional keyword arguments.
        """
        self._wrapped = wrapped
        self._invocation_id = invocation_id

    @property
    def invocation_id(self) -> str:
        """The step run invocation ID.

        Returns:
            The step run invocation ID.
        """
        return self._invocation_id

    def _wait(self) -> None:
        """Wait for the step run future to complete."""
        self._wrapped.result()


class ArtifactFuture(_BaseStepRunFuture):
    """Future for a step run output artifact."""

    def __init__(
        self, wrapped: Future[StepRunOutputs], invocation_id: str, index: int
    ) -> None:
        """Initialize the future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
            index: The index of the output artifact.
        """
        super().__init__(wrapped=wrapped, invocation_id=invocation_id)
        self._index = index

    def result(self) -> OutputArtifact:
        """Get the step run output artifact.

        Raises:
            RuntimeError: If the future returned an invalid output.

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
                f"Step {self._invocation_id} returned an invalid output: "
                f"{result}."
            )

    def load(self, disable_cache: bool = False) -> Any:
        """Load the step run output artifact data.

        Args:
            disable_cache: Whether to disable the artifact cache.

        Returns:
            The step run output artifact data.
        """
        return self.result().load(disable_cache=disable_cache)


class StepRunOutputsFuture(_BaseStepRunFuture):
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
            output_keys: The output keys of the step run.
        """
        super().__init__(wrapped=wrapped, invocation_id=invocation_id)
        self._output_keys = output_keys

    def get_artifact(self, key: str) -> ArtifactFuture:
        """Get an artifact future by key.

        Args:
            key: The key of the artifact future.

        Raises:
            KeyError: If no artifact for the given name exists.

        Returns:
            The artifact future.
        """
        if key not in self._output_keys:
            raise KeyError(
                f"Step run {self._invocation_id} does not have an output with "
                f"the name: {key}."
            )

        return ArtifactFuture(
            wrapped=self._wrapped,
            invocation_id=self._invocation_id,
            index=self._output_keys.index(key),
        )

    def artifacts(self) -> StepRunOutputs:
        """Get the step run output artifacts.

        Returns:
            The step run output artifacts.
        """
        return self._wrapped.result()

    def load(self, disable_cache: bool = False) -> Any:
        """Get the step run output artifact data.

        Args:
            disable_cache: Whether to disable the artifact cache.

        Raises:
            ValueError: If the step run output is invalid.

        Returns:
            The step run output artifact data.
        """
        result = self.artifacts()

        if result is None:
            return None
        elif isinstance(result, ArtifactVersionResponse):
            return result.load(disable_cache=disable_cache)
        elif isinstance(result, tuple):
            return tuple(
                item.load(disable_cache=disable_cache) for item in result
            )
        else:
            raise ValueError(f"Invalid step run output: {result}")

    def __getitem__(self, key: Any) -> ArtifactFuture:
        """Get an artifact future by key or index.

        Args:
            key: The key or index of the artifact future.

        Raises:
            TypeError: If the key is not an integer.
            IndexError: If the index is out of range.

        Returns:
            The artifact future.
        """
        if not isinstance(key, int):
            raise TypeError(f"Invalid key type: {type(key)}")

        # Convert to positive index if necessary
        if key < 0:
            key += len(self._output_keys)

        if key > len(self._output_keys):
            raise IndexError(f"Index out of range: {key}")

        return ArtifactFuture(
            wrapped=self._wrapped,
            invocation_id=self._invocation_id,
            index=key,
        )

    def __iter__(self) -> Any:
        """Iterate over the artifact futures.

        Raises:
            ValueError: If the step does not return any outputs.

        Yields:
            The artifact futures.
        """
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
        """Get the number of artifact futures.

        Returns:
            The number of artifact futures.
        """
        return len(self._output_keys)


StepRunFuture = Union[ArtifactFuture, StepRunOutputsFuture]
