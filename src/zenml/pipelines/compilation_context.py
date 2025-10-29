import contextvars
from typing import TYPE_CHECKING, Self

from zenml.utils import context_utils

if TYPE_CHECKING:
    from zenml.pipelines.pipeline_definition import Pipeline


class PipelineCompilationContext(context_utils.BaseContext):
    """Pipeline compilation context."""

    __context_var__ = contextvars.ContextVar("pipeline_compilation_context")

    def __init__(
        self,
        pipeline: "Pipeline",
    ) -> None:
        """Initialize the pipeline compilation context.

        Args:
            pipeline: The pipeline that is being compiled.
        """
        super().__init__()
        self._pipeline = pipeline

    @property
    def pipeline(self) -> "Pipeline":
        """The pipeline that is being compiled.

        Returns:
            The pipeline that is being compiled.
        """
        return self._pipeline

    def __enter__(self) -> Self:
        """Enter the pipeline compilation context.

        Raises:
            RuntimeError: If the pipeline compilation context has already been
                entered.

        Returns:
            The pipeline compilation context object.
        """
        if self._token is not None:
            raise RuntimeError(
                "Compiling a pipeline while another pipeline is being compiled "
                "is not allowed."
            )
        return super().__enter__()
