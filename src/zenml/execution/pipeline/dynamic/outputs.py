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

import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import Future
from contextlib import AbstractContextManager, nullcontext
from typing import (
    Any,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from zenml.enums import ExecutionStatus
from zenml.exceptions import StepExecutionException
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
    PipelineRunResponse,
    StepRunResponse,
)
from zenml.utils import exception_utils

logger = get_logger(__name__)

T = TypeVar("T")


def wrap_step_failure(
    exception: BaseException, invocation_id: Optional[str] = None
) -> StepExecutionException:
    """Wrap a step failure that was not explicitly awaited.

    Args:
        exception: The original step failure.
        invocation_id: The invocation ID of the failed step, if known.

    Returns:
        The exception unchanged if it already is a `StepExecutionException`,
        otherwise a new `StepExecutionException` chaining the original.
    """
    if isinstance(exception, StepExecutionException):
        return exception

    if invocation_id:
        message = f"Step `{invocation_id}` failed."
    else:
        message = "A step failed during pipeline execution."

    wrapped = StepExecutionException(message, original_exception=exception)
    wrapped.__cause__ = exception
    wrapped.__suppress_context__ = True
    return wrapped


def _maybe_release_pipeline_thread() -> AbstractContextManager[None]:
    """Release the current runner's pipeline thread for the duration.

    Returns a no-op context manager when called outside a dynamic
    pipeline run context, or when called from a non-pipeline thread.

    Returns:
        A context manager that releases the runner's pipeline thread.
    """
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )

    context = DynamicPipelineRunContext.get()
    if context is None:
        return nullcontext()
    runner = context.runner
    if threading.get_ident() != runner._state.id:
        return nullcontext()
    return runner._state.release()


class OutputArtifact(ArtifactVersionResponse):
    """Dynamic step run output artifact."""

    output_name: str
    step_name: str
    chunk_index: Optional[int] = None
    chunk_size: Optional[int] = None

    def chunk(self, index: int) -> "OutputArtifact":
        """Get a chunk of the output artifact.

        Args:
            index: The index of the chunk.

        Raises:
            ValueError: If the output artifact can not be chunked or the index
                is out of range.

        Returns:
            The artifact chunk.
        """
        if not self.item_count:
            raise ValueError(
                f"Output artifact `{self.output_name}` of step "
                f"`{self.step_name}` can not be chunked."
            )

        if index < 0 or index >= self.item_count:
            raise ValueError(
                f"Chunk index `{index}` out of range for output artifact "
                f"`{self.output_name}` of step `{self.step_name}`."
            )

        if self.chunk_index is not None and self.chunk_index != index:
            raise ValueError(
                f"Output artifact `{self.output_name}` of step "
                f"`{self.step_name}` is already referring to a "
                "different chunk."
            )

        return self.model_copy(update={"chunk_index": index, "chunk_size": 1})


StepRunOutputs = Union[None, OutputArtifact, Tuple[OutputArtifact, ...]]
PipelineRunOutputs = Union[
    None,
    ArtifactVersionResponse,
    Tuple[ArtifactVersionResponse, ...],
]


class BaseFuture(ABC):
    """Base future."""

    @abstractmethod
    def running(self) -> bool:
        """Check if the future is running.

        Returns:
            True if the future is running, False otherwise.
        """

    @abstractmethod
    def result(self) -> Any:
        """Get the result of the future.

        Returns:
            The result of the future.
        """


class _InlineStepFuture(BaseFuture):
    """Future for an inline step run."""

    def __init__(
        self, wrapped: Future["StepRunResponse"], invocation_id: str
    ) -> None:
        """Initialize the inline step run future.

        Args:
            wrapped: The wrapped future object.
            invocation_id: The invocation ID of the step run.
        """
        self._wrapped = wrapped
        self.invocation_id = invocation_id

    def running(self) -> bool:
        """Check if the step run future is running.

        Returns:
            True if the step run future is running, False otherwise.
        """
        return not self._wrapped.done()

    def result(self) -> "StepRunResponse":
        """Get the result of the step run future.

        Returns:
            The result of the step run future.
        """
        return self._wrapped.result()


class _IsolatedStepFuture(BaseFuture):
    """Future for an isolated step run."""

    def __init__(
        self,
        pipeline_run_id: UUID,
        invocation_id: str,
        wrapped: Optional[Future["StepRunResponse"]] = None,
    ) -> None:
        """Initialize the step run future.

        Args:
            pipeline_run_id: The ID of the pipeline run.
            invocation_id: The invocation ID of the step run.
            wrapped: Optional future to wait for that submits the step run.
        """
        self._wrapped = wrapped
        self._finished_step_run: Optional[StepRunResponse] = None
        self.pipeline_run_id = pipeline_run_id
        self.invocation_id = invocation_id

    def running(self) -> bool:
        """Check if the isolated step future is running.

        Returns:
            True if the isolated step future is running, False otherwise.
        """
        from zenml.execution.pipeline.dynamic.utils import get_latest_step_run

        if self._finished_step_run is not None:
            return False

        if self._wrapped:
            if not self._wrapped.done():
                # Waiting for the step run to be launched.
                return True

            try:
                self._wrapped.result()
            except BaseException:
                # Launching the step run failed or was cancelled.
                return False

        step_run = get_latest_step_run(
            self.pipeline_run_id, self.invocation_id, hydrate=False
        )
        if step_run.status.is_finished:
            self._finished_step_run = step_run

        return not step_run.status.is_finished

    def result(self) -> "StepRunResponse":
        """Get the result of the step future.

        Raises:
            BaseException: Any exception that happened while waiting for the
                step to finish.
            RuntimeError: If the step was stopped.

        Returns:
            The result of the step future.
        """  # noqa: DOC503
        if self._finished_step_run is not None:
            step_run = self._finished_step_run
        else:
            step_run = self._wait_for_step_to_finish()
            self._finished_step_run = step_run

        if (
            step_run.status.is_failed
            or step_run.status == ExecutionStatus.STOPPED
        ):
            raise exception_utils.reconstruct_exception(
                exception_info=step_run.exception_info,
                fallback_message=(
                    f"Step `{self.invocation_id}` failed with "
                    f"status `{step_run.status}`."
                ),
            )

        return step_run

    def _wait_for_step_to_finish(self) -> "StepRunResponse":
        """Wait until the step is finished.

        Returns:
            The finished step run.
        """
        from zenml.execution.pipeline.dynamic.utils import get_latest_step_run

        sleep_interval = 1
        max_sleep_interval = 64

        while True:
            # Re-check the wrapped future in case it got replaced.
            if wrapped := self._wrapped:
                wrapped.result()

            step_run = get_latest_step_run(
                self.pipeline_run_id, self.invocation_id, hydrate=False
            )
            # If a step is in `retrying` status, another step run will be
            # created and we will try to pick it up in the next iteration.
            if step_run.status not in {
                ExecutionStatus.PROVISIONING,
                ExecutionStatus.RUNNING,
                ExecutionStatus.RETRYING,
            }:
                return step_run

            logger.debug(
                "Waiting for step `%s` to finish (current status: %s)",
                self.invocation_id,
                step_run.status,
            )

            time.sleep(sleep_interval)
            if sleep_interval < max_sleep_interval:
                sleep_interval *= 2


StepExecutionFuture = Union[_InlineStepFuture, _IsolatedStepFuture]


class _StartupResult(Generic[T]):
    """Container for a startup result or startup exception."""

    def __init__(self) -> None:
        """Initialize the startup result."""
        self._lock = threading.Lock()
        self._future: Future[T] = Future()

    def done(self) -> bool:
        """Whether the startup completed.

        Returns:
            Whether the startup completed.
        """
        return self._future.done()

    def failed(self) -> bool:
        """Whether the startup failed.

        Returns:
            Whether the startup failed.
        """
        return self._future.done() and self._future.exception() is not None

    def result(self) -> T:
        """Get the startup result.

        Returns:
            The startup result.
        """
        return self._future.result()

    def set_result(self, value: T) -> None:
        """Store the startup result if it is still unresolved.

        Args:
            value: The startup result.
        """
        with self._lock:
            if self._future.done():
                return

            self._future.set_result(value)

    def set_exception(self, exception: BaseException) -> None:
        """Store the startup exception if it is still unresolved.

        Args:
            exception: The startup exception.
        """
        with self._lock:
            if self._future.done():
                return

            self._future.set_exception(exception)


class BaseStepFuture(BaseFuture, ABC):
    """Base step future."""

    def __init__(
        self,
        invocation_id: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the dynamic step run future.

        Args:
            invocation_id: The invocation ID of the future.
            **kwargs: Additional keyword arguments.
        """
        self._invocation_id = invocation_id

    @property
    def invocation_id(self) -> str:
        """The step run invocation ID.

        Returns:
            The step run invocation ID.
        """
        return self._invocation_id

    @abstractmethod
    def wait(self) -> None:
        """Wait for the future to finish."""


class ArtifactFuture(BaseStepFuture):
    """Future for a step run output artifact."""

    def __init__(
        self,
        parent: "StepFuture",
        index: int,
    ) -> None:
        """Initialize the future.

        Args:
            parent: The parent step future object.
            index: The index of the output artifact.
        """
        super().__init__(invocation_id=parent.invocation_id)
        self._index = index
        self._parent = parent

    def running(self) -> bool:
        """Check if the artifact future is running.

        Returns:
            True if the artifact future is running, False otherwise.
        """
        return self._parent.running()

    def result(self) -> OutputArtifact:
        """Get the output artifact this future represents.

        Raises:
            RuntimeError: If the future returned an invalid output.

        Returns:
            The output artifact.
        """
        from zenml.execution.pipeline.dynamic.utils import (
            load_step_run_outputs,
        )

        step_run = self._parent._wait()
        result = load_step_run_outputs(step_run.id)

        if isinstance(result, OutputArtifact):
            return result
        elif isinstance(result, tuple):
            return result[self._index]
        else:
            raise RuntimeError(
                f"Step {self.invocation_id} returned an invalid output: "
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

    def chunk(self, index: int) -> "OutputArtifact":
        """Get a chunk of the output artifact.

        This method will wait for the future to complete and then return the
        artifact chunk.

        Args:
            index: The index of the chunk.

        Returns:
            The artifact chunk.
        """
        return self.result().chunk(index=index)

    def wait(self) -> None:
        """Wait for the artifact future to complete."""
        self._parent.wait()


class StepFuture(BaseStepFuture):
    """Future for a step run output."""

    def __init__(
        self,
        invocation_id: str,
        output_keys: List[str],
        execution_future: Optional[StepExecutionFuture] = None,
    ) -> None:
        """Initialize the future.

        Args:
            invocation_id: The invocation ID of the step run.
            output_keys: The output keys of the step run.
            execution_future: Optional execution future if the startup has
                already completed.
        """
        super().__init__(invocation_id=invocation_id)
        self._startup = _StartupResult[StepExecutionFuture]()
        if execution_future is not None:
            self._startup.set_result(execution_future)
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
                f"Step run {self.invocation_id} does not have an output with "
                f"the name: {key}."
            )

        return ArtifactFuture(
            parent=self,
            index=self._output_keys.index(key),
        )

    def running(self) -> bool:
        """Check if the step future is running.

        Returns:
            True if the step future is running, False otherwise.
        """
        if not self._startup.done():
            return True

        if self._startup.failed():
            return False

        return self._startup.result().running()

    def wait(self) -> None:
        """Wait for the step to finish."""
        self._wait()

    def artifacts(self) -> StepRunOutputs:
        """Get the step run output artifacts.

        Returns:
            The step run output artifacts.
        """
        return self.result()

    def result(self) -> StepRunOutputs:
        """Get the step run outputs this future represents.

        Returns:
            The step run outputs.
        """
        from zenml.execution.pipeline.dynamic.utils import (
            load_step_run_outputs,
        )

        step_run = self._wait()
        return load_step_run_outputs(step_run.id)

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
                parent=self,
                index=self._output_keys.index(output_key),
            )
        elif isinstance(key, slice):
            output_keys = self._output_keys[key]
            return tuple(
                ArtifactFuture(
                    parent=self,
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
        """  # noqa: DOC201, DOC403
        if not self._output_keys:
            raise ValueError(
                f"Step {self.invocation_id} does not return any outputs."
            )

        for index in range(len(self._output_keys)):
            yield ArtifactFuture(
                parent=self,
                index=index,
            )

    def __len__(self) -> int:
        """Get the number of artifact futures.

        Returns:
            The number of artifact futures.
        """
        return len(self._output_keys)

    def _wait(self) -> StepRunResponse:
        """Wait for the step to finish.

        Returns:
            The step run response.
        """
        return self._startup.result().result()

    def _set_startup_result(self, wrapped: StepExecutionFuture) -> None:
        """Store the future that represents the started step.

        Args:
            wrapped: The future that represents the started step.
        """
        self._startup.set_result(wrapped)

    def _rebind_execution_future(self, future: StepExecutionFuture) -> None:
        """Rebind the execution future to a new attempt of the step.

        Args:
            future: The future that represents the new step execution attempt.
        """
        existing_future = self._startup.result()
        assert isinstance(future, _IsolatedStepFuture)
        assert isinstance(existing_future, _IsolatedStepFuture)

        existing_future._wrapped = future._wrapped

    def _set_startup_failed(self, exception: BaseException) -> None:
        """Store a startup exception for the step.

        Args:
            exception: The startup exception.
        """
        self._startup.set_exception(exception)

    def _cancel_startup(self, exception: BaseException) -> None:
        """Cancel step startup if it has not been resolved yet.

        Args:
            exception: The cancellation exception to store.
        """
        self._set_startup_failed(exception)


class PipelineFuture(BaseFuture):
    """Future for a child pipeline run output."""

    def __init__(
        self,
        invocation_id: str,
        declared_output_names: Optional[List[str]] = None,
    ) -> None:
        """Initialize the future.

        Args:
            invocation_id: Invocation ID of the child pipeline node.
            declared_output_names: Output names declared on the child pipeline
                entrypoint (from its return-type annotation). Empty if the
                entrypoint is unannotated; in that case effective names are
                derived from the actual outputs after execution.
        """
        self._invocation_id = invocation_id
        self._startup = _StartupResult[Future[PipelineRunResponse]]()
        self._declared_output_names = declared_output_names or []

    @property
    def invocation_id(self) -> str:
        """Invocation ID of this child pipeline future.

        Returns:
            The invocation ID.
        """
        return self._invocation_id

    def _set_startup_result(
        self, wrapped: Future[PipelineRunResponse]
    ) -> None:
        """Store the future that represents the started child pipeline run.

        Args:
            wrapped: The future that resolves to the pipeline run.
        """
        self._startup.set_result(wrapped)

    def _set_startup_failed(self, exception: BaseException) -> None:
        """Store a startup exception for the child pipeline.

        Args:
            exception: The startup exception.
        """
        self._startup.set_exception(exception)

    def _cancel_startup(self, exception: BaseException) -> None:
        """Cancel child pipeline startup if it has not been resolved yet.

        Args:
            exception: The cancellation exception to store.
        """
        self._set_startup_failed(exception)

    def running(self) -> bool:
        """Check if the child pipeline future is running.

        Returns:
            True if the future is running, False otherwise.
        """
        if not self._startup.done():
            return True
        if self._startup.failed():
            return False

        return not self._startup.result().done()

    def wait(self) -> None:
        """Wait for the child pipeline to finish."""
        with _maybe_release_pipeline_thread():
            self._startup.result().result()

    def result(self) -> PipelineRunOutputs:
        """Get the child pipeline outputs.

        Returns:
            The child pipeline outputs.
        """
        from zenml.execution.pipeline.dynamic.utils import (
            load_pipeline_run_outputs,
        )

        with _maybe_release_pipeline_thread():
            run = self._startup.result().result()
        return load_pipeline_run_outputs(run=run)

    def artifacts(self) -> PipelineRunOutputs:
        """Get the child pipeline output artifacts.

        Returns:
            The child pipeline output artifacts.
        """
        return self.result()

    def get_artifact(self, key: str) -> ArtifactVersionResponse:
        """Get an output artifact by output name.

        Args:
            key: The output name.

        Raises:
            KeyError: If no output exists for the key.

        Returns:
            The output artifact.
        """
        outputs = self._output_tuple()
        names = self._effective_output_names(count=len(outputs))
        if key not in names:
            raise KeyError(
                f"Child pipeline `{self.invocation_id}` does not have an output "
                f"with the name `{key}`."
            )
        return outputs[names.index(key)]

    def _output_tuple(self) -> Tuple["ArtifactVersionResponse", ...]:
        """Normalize outputs to tuple form.

        Returns:
            Outputs as tuple.
        """
        result = self.result()
        if result is None:
            return ()
        if isinstance(result, ArtifactVersionResponse):
            return (result,)
        return result

    def _effective_output_names(self, count: int) -> List[str]:
        """Resolve effective output names matching what the server persisted.

        Args:
            count: Number of output artifacts actually produced.

        Returns:
            Output names in deterministic order.
        """
        from zenml.execution.pipeline.dynamic.pipeline_output_utils import (
            resolve_pipeline_output_names,
        )

        return resolve_pipeline_output_names(
            declared_names=self._declared_output_names, count=count
        )

    @overload
    def __getitem__(self, key: int) -> ArtifactVersionResponse: ...

    @overload
    def __getitem__(
        self, key: slice
    ) -> Tuple[ArtifactVersionResponse, ...]: ...

    def __getitem__(
        self, key: Union[int, slice]
    ) -> Union[
        ArtifactVersionResponse,
        Tuple[ArtifactVersionResponse, ...],
    ]:
        """Get output artifact(s) by index.

        Args:
            key: Index or slice.

        Returns:
            Output artifact(s).
        """
        return self._output_tuple()[key]

    def __iter__(self) -> Iterator[ArtifactVersionResponse]:
        """Iterate over output artifacts.

        Yields:
            Output artifacts.
        """
        yield from self._output_tuple()

    def __len__(self) -> int:
        """Get the declared number of output artifacts.

        Returns the count from the entrypoint's return-type annotation. This
        is non-blocking and may be `0` if the entrypoint is unannotated; in
        that case use `len(future.result())` to get the actual count.

        Returns:
            Number of declared output artifacts.
        """
        return len(self._declared_output_names)


class MapResultsFuture(BaseFuture):
    """Future that represents the results of a `step.map/product(...)` call."""

    def __init__(self, invocation_id: str) -> None:
        """Initialize an empty map results future.

        Args:
            invocation_id: Stable invocation ID for the map expansion.
        """
        self._invocation_id = invocation_id
        self._startup = _StartupResult[List[StepFuture]]()

    @property
    def invocation_id(self) -> str:
        """Stable invocation ID for this map expansion.

        Returns:
            The invocation ID.
        """
        return self._invocation_id

    @property
    def startup_succeeded(self) -> bool:
        """Whether map startup completed successfully with child futures.

        Returns:
            Whether the  startup completed successfully.
        """
        return self._startup.done() and not self._startup.failed()

    @property
    def startup_failed(self) -> bool:
        """Whether the map startup failed.

        Returns:
            Whether the map startup failed.
        """
        return self._startup.failed()

    def _set_startup_result(self, futures: List[StepFuture]) -> None:
        """Store the child step futures created for the map.

        Args:
            futures: The child step futures created for the map.
        """
        self._startup.set_result(futures)

    def _set_startup_failed(self, exception: BaseException) -> None:
        """Store a startup exception for the map.

        Args:
            exception: The startup exception.
        """
        self._startup.set_exception(exception)

    def _cancel_startup(self, exception: BaseException) -> None:
        """Cancel map startup if it has not been resolved yet.

        Args:
            exception: The cancellation exception to store.
        """
        self._set_startup_failed(exception)

    @property
    def futures(self) -> List[StepFuture]:
        """Get the child step futures for the map.

        Returns:
            The child step futures.
        """
        return self._startup.result()

    def running(self) -> bool:
        """Check if the map results future is running.

        Returns:
            True if the map results future is running, False otherwise.
        """
        if not self._startup.done():
            return True
        if self._startup.failed():
            return False
        return any(future.running() for future in self.futures)

    def wait(self) -> None:
        """Wait for the map results future to complete."""
        for future in self.futures:
            future.wait()

    def result(self) -> List[StepRunOutputs]:
        """Get the step run outputs this future represents.

        Returns:
            The step run outputs.
        """
        return [future.result() for future in self.futures]

    def load(self, disable_cache: bool = False) -> List[Any]:
        """Load the step run output artifacts.

        Args:
            disable_cache: Whether to disable the artifact cache.

        Returns:
            The step run output artifacts.
        """
        return [
            future.load(disable_cache=disable_cache) for future in self.futures
        ]

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
    def __getitem__(self, key: int) -> StepFuture: ...

    @overload
    def __getitem__(self, key: slice) -> List[StepFuture]: ...

    def __getitem__(
        self, key: Union[int, slice]
    ) -> Union[StepFuture, List[StepFuture]]:
        """Get a step run future.

        Args:
            key: The index or slice of the step run futures.

        Returns:
            The step run futures.
        """
        return self.futures[key]

    def __iter__(self) -> Iterator[StepFuture]:
        """Iterate over the step run futures.

        Yields:
            The step run futures.
        """  # noqa: DOC403
        yield from self.futures

    def __len__(self) -> int:
        """Get the number of step run futures.

        Returns:
            The number of step run futures.
        """
        return len(self.futures)


AnyOutputFuture = Union[
    ArtifactFuture,
    StepFuture,
    MapResultsFuture,
    PipelineFuture,
]
AnyStepFuture = AnyOutputFuture  # Backwards compatibility alias
