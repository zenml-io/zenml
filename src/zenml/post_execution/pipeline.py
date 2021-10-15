from typing import TYPE_CHECKING, List

from tfx.dsl.compiler.constants import PIPELINE_RUN_CONTEXT_TYPE_NAME

from zenml.logger import get_logger
from zenml.post_execution.pipeline_run import PipelineRunView

if TYPE_CHECKING:
    from zenml.metadata.base_metadata_store import BaseMetadataStore

logger = get_logger(__name__)


class PipelineView:
    """Post-execution pipeline class which can be used to query
    pipeline-related information from the metadata store.
    """

    def __init__(
        self, id_: int, name: str, metadata_store: "BaseMetadataStore"
    ):
        """Initializes a post-execution pipeline object.

        In most cases `PipelineView` objects should not be created manually
        but retrieved using the `get_pipelines()` method of a
        `zenml.core.repo.Repository` instead.

        Args:
            id_: The context id of this pipeline.
            name: The name of this pipeline.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this pipeline.
        """
        self._id = id_
        self._name = name
        self._metadata_store = metadata_store
        self._runs: List[PipelineRunView] = []

    @property
    def name(self) -> str:
        """Returns the name of the pipeline."""
        return self._name

    def get_runs(self) -> List[PipelineRunView]:
        """Returns all stored runs of this pipeline.

        The runs are returned in chronological order, so the latest
        run will be the last element in this list.
        """
        self._ensure_runs_fetched()
        return self._runs

    def _ensure_runs_fetched(self) -> None:
        """Fetches all runs for this pipeline from the metadata store."""
        if self._runs:
            # we already fetched the runs, no need to do anything
            return

        all_pipeline_runs = self._metadata_store.store.get_contexts_by_type(
            PIPELINE_RUN_CONTEXT_TYPE_NAME
        )

        for run in all_pipeline_runs:
            run_executions = (
                self._metadata_store.store.get_executions_by_context(run.id)
            )
            if run_executions:
                associated_contexts = (
                    self._metadata_store.store.get_contexts_by_execution(
                        run_executions[0].id
                    )
                )
                for context in associated_contexts:
                    if context.id == self._id:
                        # Run is of this pipeline
                        self._runs.append(
                            PipelineRunView(
                                id_=run.id,
                                name=run.name,
                                executions=run_executions,
                                metadata_store=self._metadata_store,
                            )
                        )
                        break

        logger.debug(
            "Fetched %d pipeline runs for '%s'.", len(self._runs), self._name
        )

    def __repr__(self) -> str:
        """Returns a string representation of this pipeline."""
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"name='{self._name}')"
        )
