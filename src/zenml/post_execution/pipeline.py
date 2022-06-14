#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the post-execution pipeline."""

from typing import TYPE_CHECKING, Any, List, Optional

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

if TYPE_CHECKING:
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.post_execution.pipeline_run import PipelineRunView

logger = get_logger(__name__)


class PipelineView:
    """Post-execution pipeline class.

    This can be used to query pipeline-related information from the metadata store.
    """

    def __init__(
        self, id_: int, name: str, metadata_store: "BaseMetadataStore"
    ):
        """Initializes a post-execution pipeline object.

        In most cases `PipelineView` objects should not be created manually
        but retrieved using the `get_pipelines()` method of a
        `zenml.repository.Repository` instead.

        Args:
            id_: The context id of this pipeline.
            name: The name of this pipeline.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this pipeline.
        """
        self._id = id_
        self._name = name
        self._metadata_store = metadata_store

    @property
    def name(self) -> str:
        """Returns the name of the pipeline.

        Returns:
            The name of the pipeline.
        """
        return self._name

    @property
    def runs(self) -> List["PipelineRunView"]:
        """Returns all stored runs of this pipeline.

        The runs are returned in chronological order, so the latest
        run will be the last element in this list.

        Returns:
            A list of all stored runs of this pipeline.
        """
        # Do not cache runs as new runs might appear during this objects
        # lifecycle
        runs = list(self._metadata_store.get_pipeline_runs(self).values())

        for run in runs:
            run._run_wrapper = self._get_zenstore_run(run_name=run.name)

        return runs

    def get_run_names(self) -> List[str]:
        """Returns a list of all run names.

        Returns:
            A list of all run names.
        """
        # Do not cache runs as new runs might appear during this objects
        # lifecycle
        runs = self._metadata_store.get_pipeline_runs(self)
        return list(runs.keys())

    def get_run(self, name: str) -> "PipelineRunView":
        """Returns a run for the given name.

        Args:
            name: The name of the run to return.

        Returns:
            The run with the given name.

        Raises:
            KeyError: If there is no run with the given name.
        """
        run = self._metadata_store.get_pipeline_run(self, name)

        if not run:
            raise KeyError(
                f"No run found for name `{name}`. This pipeline "
                f"only has runs with the following "
                f"names: `{self.get_run_names()}`"
            )

        run._run_wrapper = self._get_zenstore_run(run_name=name)
        return run

    def get_run_for_completed_step(self, step_name: str) -> "PipelineRunView":
        """Ascertains which pipeline run produced the cached artifact of a given step.

        Args:
            step_name: Name of step at hand

        Returns:
            None if no run is found that completed the given step,
                else the original pipeline_run.

        Raises:
            LookupError: If no run is found that completed the given step
        """
        orig_pipeline_run = None

        for run in reversed(self.runs):
            try:
                step = run.get_step(step_name)
                if step.is_completed:
                    orig_pipeline_run = run
                    break
            except KeyError:
                pass
        if not orig_pipeline_run:
            raise LookupError(
                "No Pipeline Run could be found, that has"
                f" completed the provided step: [{step_name}]"
            )

        return orig_pipeline_run

    def _get_zenstore_run(self, run_name: str) -> Optional[PipelineRunWrapper]:
        """Gets a ZenStore run for the given run name.

        This will filter all ZenStore runs by the pipeline name of this
        pipeline view, the run name passed in as an argument and the metadata
        store that this pipeline run is associated with.

        Args:
            run_name: The name of the run to get.

        Returns:
            The ZenStore run with the given name, if found.
        """
        from zenml.repository import Repository

        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        try:
            run_wrapper = repo.zen_store.get_pipeline_run(
                pipeline_name=self.name, run_name=run_name
            )
            metadata_store_wrapper = run_wrapper.stack.get_component_wrapper(
                StackComponentType.METADATA_STORE
            )
            if metadata_store_wrapper and (
                metadata_store_wrapper.uuid == self._metadata_store.uuid
            ):
                return run_wrapper
        except KeyError:
            pass

        return None

    def __repr__(self) -> str:
        """Returns a string representation of this pipeline.

        Returns:
            A string representation of this pipeline.
        """
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"name='{self._name}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same pipeline.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same pipeline,
            False otherwise.
        """
        if isinstance(other, PipelineView):
            return (
                self._id == other._id
                and self._metadata_store.uuid == other._metadata_store.uuid
            )
        return NotImplemented
