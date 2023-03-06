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
"""Implementation of the post-execution pipeline run class."""

from collections import OrderedDict
from functools import partial
from typing import Any, Dict, List, Optional, cast

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.logger import get_apidocs_link, get_logger
from zenml.models import PipelineRunResponseModel
from zenml.post_execution.base_view import BaseView
from zenml.post_execution.step import StepView
from zenml.utils.pagination_utils import depaginate

logger = get_logger(__name__)


def get_run(name: str) -> "PipelineRunView":
    """Fetches the post-execution view of a run with the given name.

    Args:
        name: The name of the run to fetch.

    Returns:
        The post-execution view of the run with the given name.

    Raises:
        KeyError: If no run with the given name exists.
        RuntimeError: If multiple runs with the given name exist.
    """
    client = Client()
    active_workspace_id = client.active_workspace.id
    runs = client.list_runs(
        name=name,
        workspace_id=active_workspace_id,
    )

    # TODO: [server] this error handling could be improved
    if not runs:
        raise KeyError(f"No run with name '{name}' exists.")
    elif runs.total > 1:
        raise RuntimeError(
            f"Multiple runs have been found for name  '{name}'.", runs
        )
    return PipelineRunView(runs.items[0])


def get_unlisted_runs() -> List["PipelineRunView"]:
    """Fetches the post-execution views of the 50 most recent unlisted runs.

    Unlisted runs are runs that are not associated with any pipeline.

    Returns:
        A list of post-execution run views.
    """
    client = Client()
    runs = client.list_runs(
        workspace_id=client.active_workspace.id,
        unlisted=True,
        size=50,
        sort_by="desc:created",
    )
    return [PipelineRunView(model) for model in runs.items]


class PipelineRunView(BaseView):
    """Post-execution pipeline run class.

    This can be used to query steps and artifact information associated with a
    pipeline execution.
    """

    MODEL_CLASS = PipelineRunResponseModel
    REPR_KEYS = ["id", "name"]

    def __init__(self, model: PipelineRunResponseModel):
        """Initializes a post-execution pipeline run object.

        In most cases `PipelineRunView` objects should not be created manually
        but retrieved from a `PipelineView` object instead.

        Args:
            model: The model to initialize this object from.
        """
        super().__init__(model)
        self._steps: Dict[str, StepView] = OrderedDict()

    @property
    def model(self) -> PipelineRunResponseModel:
        """Returns the underlying `PipelineRunResponseModel`.

        Returns:
            The underlying `PipelineRunResponseModel`.
        """
        return cast(PipelineRunResponseModel, self._model)

    @property
    def settings(self) -> Dict[str, Any]:
        """Returns the pipeline settings.

        These are runtime settings passed down to stack components, which
        can be set at pipeline level.

        Returns:
            The pipeline settings.
        """
        settings = self.model.pipeline_configuration["settings"]
        return cast(Dict[str, Any], settings)

    @property
    def extra(self) -> Dict[str, Any]:
        """Returns the pipeline extras.

        This dict is meant to be used to pass any configuration down to the
        pipeline or stack components that the user has use of.

        Returns:
            The pipeline extras.
        """
        extra = self.model.pipeline_configuration["extra"]
        return cast(Dict[str, Any], extra)

    @property
    def enable_cache(self) -> Optional[bool]:
        """Returns whether caching is enabled for this pipeline run.

        Returns:
            True if caching is enabled for this pipeline run.
        """
        from zenml.pipelines.base_pipeline import PARAM_ENABLE_CACHE

        return self.model.pipeline_configuration.get(PARAM_ENABLE_CACHE)

    @property
    def enable_artifact_metadata(self) -> Optional[bool]:
        """Returns whether artifact metadata is enabled for this pipeline run.

        Returns:
            True if artifact metadata is enabled for this pipeline run.
        """
        from zenml.pipelines.base_pipeline import (
            PARAM_ENABLE_ARTIFACT_METADATA,
        )

        return self.model.pipeline_configuration.get(
            PARAM_ENABLE_ARTIFACT_METADATA
        )

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the pipeline run.

        Returns:
            The current status of the pipeline run.
        """
        # Query the run again since the status might have changed since this
        # object was created.
        return Client().get_pipeline_run(self.model.id).status

    @property
    def steps(self) -> List[StepView]:
        """Returns all steps that were executed as part of this pipeline run.

        Returns:
            A list of all steps that were executed as part of this pipeline run.
        """
        self._ensure_steps_fetched()
        return list(self._steps.values())

    def get_step_names(self) -> List[str]:
        """Returns a list of all step names.

        Returns:
            A list of all step names.
        """
        self._ensure_steps_fetched()
        return list(self._steps.keys())

    def get_step(
        self,
        step: Optional[str] = None,
        **kwargs: Any,
    ) -> StepView:
        """Returns a step for the given name.

        The name refers to the name of the step in the pipeline definition, not
        the class name of the step-class.

        Use it like this:
        ```python
        # Get the step by name
        pipeline_run_view.get_step("first_step")
        ```

        Args:
            step: Class or class instance of the step
            **kwargs: The deprecated `name` is caught as a kwarg to
                specify the step instead of using the `step` argument.

        Returns:
            A step for the given name.

        Raises:
            KeyError: If there is no step with the given name.
            RuntimeError: If no step has been specified at all.
        """
        self._ensure_steps_fetched()

        api_doc_link = get_apidocs_link(
            "core-post_execution",
            "zenml.post_execution.pipeline_run.PipelineRunView" ".get_step",
        )
        step_name = kwargs.get("name", None)

        # Raise an error if neither `step` nor `name` args were provided.
        if not step and not isinstance(step_name, str):
            raise RuntimeError(
                "No step specified. Please specify a step using "
                "pipeline_run_view.get_step(step=`step_name`). "
                f"Please refer to the API docs to learn more: "
                f"{api_doc_link}"
            )

        # If `name` was provided but not `step`, print a depreciation warning.
        if not step:
            logger.warning(
                "Using 'name' to get a step from "
                "'PipelineRunView.get_step()' is deprecated and "
                "will be removed in the future. Instead please "
                "use 'step' to access a step from your past "
                "pipeline runs. Learn more in our API docs: %s",
                api_doc_link,
            )
            step = step_name

        # Raise an error if there is no such step in the given pipeline run.
        if step not in self._steps:
            raise KeyError(
                f"No step found for name `{step}`. This pipeline "
                f"run only has steps with the following "
                f"names: `{self.get_step_names()}`"
            )

        return self._steps[step]

    def _ensure_steps_fetched(self) -> None:
        """Fetches all steps for this pipeline run from the metadata store."""
        if self._steps:
            # we already fetched the steps, no need to do anything
            return

        client = Client()
        steps = depaginate(
            partial(client.list_run_steps, pipeline_run_id=self.model.id)
        )

        self._steps = {step.name: StepView(step) for step in steps}
