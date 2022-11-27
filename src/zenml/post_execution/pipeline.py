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

from typing import TYPE_CHECKING, Any, List, Optional, Type, Union
from uuid import UUID

from zenml.client import Client
from zenml.logger import get_apidocs_link, get_logger
from zenml.models import PipelineResponseModel
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.utils.analytics_utils import AnalyticsEvent, track

if TYPE_CHECKING:
    from zenml.config.pipeline_configurations import PipelineSpec
    from zenml.pipelines.base_pipeline import BasePipeline

logger = get_logger(__name__)


@track(event=AnalyticsEvent.GET_PIPELINES)
def get_pipelines() -> List["PipelineView"]:
    """Fetches all post-execution pipeline views in the active project.

    Returns:
        A list of post-execution pipeline views.
    """
    # TODO: [server] handle the active stack correctly
    client = Client()
    pipelines = client.zen_store.list_pipelines(
        project_name_or_id=client.active_project.id
    )
    return [PipelineView(model) for model in pipelines]


@track(event=AnalyticsEvent.GET_PIPELINE)
def get_pipeline(
    pipeline: Optional[Union["BasePipeline", Type["BasePipeline"], str]] = None,
    **kwargs: Any,
) -> Optional["PipelineView"]:
    """Fetches a post-execution pipeline view.

    Use it in one of these ways:
    ```python
    from zenml.post_execution import get_pipeline

    # Get the pipeline by name
    get_pipeline("first_pipeline")

    # Get the pipeline by supplying the original pipeline class
    get_pipeline(first_pipeline)

    # Get the pipeline by supplying an instance of the original pipeline class
    get_pipeline(first_pipeline())
    ```

    If the specified pipeline does not (yet) exist within the repository,
    `None` will be returned.

    Args:
        pipeline: Class or class instance of the pipeline
        **kwargs: The deprecated `pipeline_name` is caught as a kwarg to
            specify the pipeline instead of using the `pipeline` argument.

    Returns:
        A post-execution pipeline view for the given pipeline or `None` if
        it doesn't exist.

    Raises:
        RuntimeError: If the pipeline was not specified correctly.
    """
    from zenml.pipelines.base_pipeline import BasePipeline

    if isinstance(pipeline, str):
        pipeline_name = pipeline
    elif isinstance(pipeline, BasePipeline):
        pipeline_name = pipeline.name
    elif isinstance(pipeline, type) and issubclass(pipeline, BasePipeline):
        pipeline_name = pipeline.__name__
    elif "pipeline_name" in kwargs and isinstance(
        kwargs.get("pipeline_name"), str
    ):
        logger.warning(
            "Using 'pipeline_name' to get a pipeline from "
            "'get_pipeline()' is deprecated and "
            "will be removed in the future. Instead please "
            "use 'pipeline' to access a pipeline in your Repository based "
            "on the name of the pipeline or even the class or instance "
            "of the pipeline. Learn more in our API docs: %s",
            get_apidocs_link(
                "core-repository", "zenml.post_execution.pipeline.get_pipeline"
            ),
        )

        pipeline_name = kwargs.pop("pipeline_name")
    else:
        raise RuntimeError(
            "No pipeline specified. Please set a `pipeline` "
            "within the `get_pipeline()` method. Learn more "
            "in our API docs: %s",
            get_apidocs_link(
                "core-repository", "zenml.post_execution.pipeline.get_pipeline"
            ),
        )

    client = Client()
    active_project_id = client.active_project.id

    pipeline_models = client.list_pipelines(
        name=pipeline_name,
        project_name_or_id=active_project_id,
    )
    if len(pipeline_models) == 1:
        return PipelineView(pipeline_models[0])
    elif len(pipeline_models) > 1:
        raise RuntimeError(
            f"Pipeline_name `{pipeline_name}` not unique within Project "
            f"`{active_project_id}`."
        )
    else:
        return None


class PipelineView:
    """Post-execution pipeline class."""

    def __init__(self, model: PipelineResponseModel):
        """Initializes a post-execution pipeline object.

        In most cases `PipelineView` objects should not be created manually
        but retrieved using the `get_pipelines()` utility from
        `zenml.post_execution` instead.

        Args:
            model: The model to initialize this pipeline view from.
        """
        self._model = model

    @property
    def id(self) -> UUID:
        """Returns the ID of this pipeline.

        Returns:
            The ID of this pipeline.
        """
        assert self._model.id is not None
        return self._model.id

    @property
    def name(self) -> str:
        """Returns the name of the pipeline.

        Returns:
            The name of the pipeline.
        """
        return self._model.name

    @property
    def docstring(self) -> Optional[str]:
        """Returns the docstring of the pipeline.

        Returns:
            The docstring of the pipeline.
        """
        return self._model.docstring

    @property
    def spec(self) -> "PipelineSpec":
        """Returns the spec of the pipeline.

        The pipeline spec contains the source paths of all steps, as well as
        each of their upstream step names. This is primarily used to compare
        whether two pipelines are the same.

        Returns:
            The spec of the pipeline.
        """
        return self._model.spec

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
        active_project_id = Client().active_project.id
        runs = Client().zen_store.list_runs(
            project_name_or_id=active_project_id,
            pipeline_id=self._model.id,
        )
        return [PipelineRunView(run) for run in runs]

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

    def __repr__(self) -> str:
        """Returns a string representation of this pipeline.

        Returns:
            A string representation of this pipeline.
        """
        return (
            f"{self.__class__.__qualname__}(id={self.id}, "
            f"name='{self.name}')"
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
            return self.id == other.id
        return NotImplemented
