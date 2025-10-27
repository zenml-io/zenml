import contextvars
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse
    from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
    from zenml.pipelines.dynamic.runner import DynamicPipelineRunner


class BaseContext:
    __context_var__: ClassVar[contextvars.ContextVar[Self]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._token: Optional[contextvars.Token[Any]] = None

    @classmethod
    def get(cls: type[Self]) -> Optional[Self]:
        return cls.__context_var__.get(None)

    def __enter__(self) -> Self:
        self._token = self.__context_var__.set(self)
        return self

    def __exit__(self, *_: Any) -> None:
        if not self._token:
            raise RuntimeError(
                f"Can't exit {self.__class__.__name__} because it has not been "
                "entered."
            )
        self.__context_var__.reset(self._token)


class DynamicPipelineRunContext(BaseContext):
    __context_var__ = contextvars.ContextVar("dynamic_pipeline_run_context")

    def __init__(
        self,
        pipeline: "DynamicPipeline",
        snapshot: "PipelineSnapshotResponse",
        run: "PipelineRunResponse",
        runner: "DynamicPipelineRunner",
    ) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._snapshot = snapshot
        self._run = run
        self._runner = runner

    @property
    def pipeline(self) -> "DynamicPipeline":
        return self._pipeline

    @property
    def run(self) -> "PipelineRunResponse":
        return self._run

    @property
    def snapshot(self) -> "PipelineSnapshotResponse":
        return self._snapshot

    @property
    def runner(self) -> "DynamicPipelineRunner":
        return self._runner

    def __enter__(self) -> Self:
        if self._token is not None:
            raise RuntimeError(
                "Calling a pipeline within a dynamic pipeline is not allowed."
            )
        return super().__enter__()


def executing_dynamic_pipeline() -> bool:
    return DynamicPipelineRunContext.get() is not None
