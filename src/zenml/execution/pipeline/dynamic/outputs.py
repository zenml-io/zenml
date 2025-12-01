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
from typing import Any, Iterator, List, Optional, Tuple, Union, overload

from zenml.logger import get_logger
from zenml.models import ArtifactVersionResponse

logger = get_logger(__name__)


class OutputArtifact(ArtifactVersionResponse):
    """Dynamic step run output artifact."""

    output_name: str
    step_name: str
    chunk_index: Optional[int] = None
    chunk_size: Optional[int] = None


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
        """Get the output artifact this future represents.

        Raises:
            RuntimeError: If the future returned an invalid output.

        Returns:
            The output artifact.
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

    def result(self) -> StepRunOutputs:
        """Get the step run outputs this future represents.

        Returns:
            The step run outputs.
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

    @overload
    def __getitem__(self, key: int) -> ArtifactFuture: ...

    @overload
    def __getitem__(self, key: slice) -> Tuple[ArtifactFuture, ...]: ...

    def __getitem__(
        self, key: Union[int, slice]
    ) -> Union[ArtifactFuture, Tuple[ArtifactFuture, ...]]:
        """Get an artifact future.

        Args:
            key: The index or slice of the artifact futures.

        Raises:
            TypeError: If the key is not an integer or slice.

        Returns:
            The artifact futures.
        """
        if isinstance(key, int):
            output_key = self._output_keys[key]

            return ArtifactFuture(
                wrapped=self._wrapped,
                invocation_id=self._invocation_id,
                index=self._output_keys.index(output_key),
            )
        elif isinstance(key, slice):
            output_keys = self._output_keys[key]
            return tuple(
                ArtifactFuture(
                    wrapped=self._wrapped,
                    invocation_id=self._invocation_id,
                    index=self._output_keys.index(output_key),
                )
                for output_key in output_keys
            )
        else:
            raise TypeError(f"Invalid key type: {type(key)}")

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


class MapResultsFuture:
    """Future that represents the results of a `step.map/product(...)` call."""

    def __init__(self, futures: List[StepRunOutputsFuture]) -> None:
        """Initialize the map results future.

        Args:
            futures: The step run futures.
        """
        self.futures = futures

    def result(self) -> List[StepRunOutputs]:
        """Get the step run outputs this future represents.

        Returns:
            The step run outputs.
        """
        return [future.result() for future in self.futures]

    def unpack(self) -> Tuple[List[ArtifactFuture], ...]:
        """Unpack the map results future.

        This method can be used to get lists of artifact futures that represent
        the outputs of all the step runs that are part of this map result.

        Example:
        ```python
        from zenml import pipeline, step

        @step
        def create_int_list() -> list[int]:
            return [1, 2]

        @step
        def do_something(a: int) -> Tuple[int, int]:
            return a * 2, a * 3

        @pipeline
        def map_pipeline():
            int_list = create_int_list()
            results = do_something.map(a=int_list)
            double, triple = results.unpack()

            # [future.load() for future in double] will return [2, 4]
            # [future.load() for future in triple] will return [3, 6]
        ```

        Returns:
            The unpacked map results.
        """
        return tuple(map(list, zip(*self.futures)))

    @overload
    def __getitem__(self, key: int) -> StepRunOutputsFuture: ...

    @overload
    def __getitem__(self, key: slice) -> List[StepRunOutputsFuture]: ...

    def __getitem__(
        self, key: Union[int, slice]
    ) -> Union[StepRunOutputsFuture, List[StepRunOutputsFuture]]:
        """Get a step run future.

        Args:
            key: The index or slice of the step run futures.

        Returns:
            The step run futures.
        """
        return self.futures[key]

    def __iter__(self) -> Iterator[StepRunOutputsFuture]:
        """Iterate over the step run futures.

        Yields:
            The step run futures.
        """
        yield from self.futures

    def __len__(self) -> int:
        """Get the number of step run futures.

        Returns:
            The number of step run futures.
        """
        return len(self.futures)


StepRunFuture = Union[ArtifactFuture, StepRunOutputsFuture, MapResultsFuture]
