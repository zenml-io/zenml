#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import TYPE_CHECKING, Any, List, Optional, Type, Union, cast

from zenml.client import Client
from zenml.logger import get_apidocs_link, get_logger
from zenml.models import PipelineResponseModel, PipelineRunFilterModel
from zenml.post_execution.base_view import BaseView
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.utils.analytics_utils import AnalyticsEvent, track

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline

logger = get_logger(__name__)


@track(event=AnalyticsEvent.GET_PIPELINES)
def get_pipelines() -> List["PipelineView"]:
    """Fetches all post-execution pipeline views in the active workspace.

    Returns:
        A list of post-execution pipeline views.
    """
    # TODO: [server] handle the active stack correctly
    client = Client()
    pipelines = client.list_pipelines(
        workspace_id=client.active_workspace.id,
        sort_by="desc:created",
    )
    return [PipelineView(model) for model in pipelines.items]


@track(event=AnalyticsEvent.GET_PIPELINE)
def get_pipeline(
    pipeline: Optional[
        Union["BasePipeline", Type["BasePipeline"], str]
    ] = None,
    version: Optional[str] = None,
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
        pipeline: Name, class or instance of the pipeline.
        version: Optional version of the pipeline. If not given, the latest
            version will be returned.
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
        pipeline_model = pipeline._get_registered_model()
        if pipeline_model:
            return PipelineView(model=pipeline_model)
        else:
            return None
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
    try:
        pipeline_model = client.get_pipeline(
            name_id_or_prefix=pipeline_name, version=version
        )
        return PipelineView(model=pipeline_model)
    except KeyError:
        return None


class PipelineView(BaseView):
    """Post-execution pipeline class."""

    MODEL_CLASS = PipelineResponseModel
    REPR_KEYS = ["id", "name"]

    @property
    def model(self) -> PipelineResponseModel:
        """Returns the underlying `PipelineResponseModel`.

        Returns:
            The underlying `PipelineResponseModel`.
        """
        return cast(PipelineResponseModel, self._model)

    @property
    def num_runs(self) -> int:
        """Returns the number of runs of this pipeline.

        Returns:
            The number of runs of this pipeline.
        """
        active_workspace_id = Client().active_workspace.id
        return (
            Client()
            .zen_store.list_runs(
                PipelineRunFilterModel(
                    workspace_id=active_workspace_id,
                    pipeline_id=self._model.id,
                )
            )
            .total
        )

    @property
    def runs(self) -> List["PipelineRunView"]:
        """Returns the last 50 stored runs of this pipeline.

        The runs are returned in reverse chronological order, so the latest
        run will be the first element in this list.

        Returns:
            A list of all stored runs of this pipeline.
        """
        # Do not cache runs as new runs might appear during this objects
        # lifecycle
        active_workspace_id = Client().active_workspace.id
        runs = Client().list_runs(
            workspace_id=active_workspace_id,
            pipeline_id=self.model.id,
            size=50,
            sort_by="desc:created",
        )

        return [PipelineRunView(run) for run in runs.items]

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
