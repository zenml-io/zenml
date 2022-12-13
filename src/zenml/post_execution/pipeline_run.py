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
"""Implementation of the post-execution pipeline run class."""

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.logger import get_apidocs_link, get_logger
from zenml.models import PipelineRunResponseModel
from zenml.post_execution.step import StepView

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
    active_project_id = client.active_project.id
    runs = client.zen_store.list_runs(
        name=name,
        project_name_or_id=active_project_id,
    )

    # TODO: [server] this error handling could be improved
    if not runs:
        raise KeyError(f"No run with name '{name}' exists.")
    elif len(runs) > 1:
        raise RuntimeError(
            f"Multiple runs have been found for name  '{name}'.", runs
        )
    return PipelineRunView(runs[0])


def get_unlisted_runs() -> List["PipelineRunView"]:
    """Fetches post-execution views of all unlisted runs.

    Unlisted runs are runs that are not associated with any pipeline.

    Returns:
        A list of post-execution run views.
    """
    client = Client()
    runs = client.zen_store.list_runs(
        project_name_or_id=client.active_project.id,
        unlisted=True,
    )
    return [PipelineRunView(model) for model in runs]


class PipelineRunView:
    """Post-execution pipeline run class.

    This can be used to query steps and artifact information associated with a
    pipeline execution.
    """

    def __init__(self, model: PipelineRunResponseModel):
        """Initializes a post-execution pipeline run object.

        In most cases `PipelineRunView` objects should not be created manually
        but retrieved from a `PipelineView` object instead.

        Args:
            model: The model to initialize this object from.
        """
        self._model = model
        self._steps: Dict[str, StepView] = OrderedDict()

    @property
    def id(self) -> UUID:
        """Returns the ID of this pipeline run.

        Returns:
            The ID of this pipeline run.
        """
        assert self._model.id is not None
        return self._model.id

    @property
    def name(self) -> str:
        """Returns the name of the pipeline run.

        Returns:
            The name of the pipeline run.
        """
        return self._model.name

    @property
    def pipeline_configuration(self) -> Dict[str, Any]:
        """Returns the pipeline configuration.

        Returns:
            The pipeline configuration.
        """
        return self._model.pipeline_configuration

    @property
    def settings(self) -> Dict[str, Any]:
        """Returns the pipeline settings.

        These are runtime settings passed down to stack components, which
        can be set at pipeline level.

        Returns:
            The pipeline settings.
        """
        settings = self.pipeline_configuration["settings"]
        return cast(Dict[str, Any], settings)

    @property
    def extra(self) -> Dict[str, Any]:
        """Returns the pipeline extras.

        This dict is meant to be used to pass any configuration down to the
        pipeline or stack components that the user has use of.

        Returns:
            The pipeline extras.
        """
        extra = self.pipeline_configuration["extra"]
        return cast(Dict[str, Any], extra)

    @property
    def enable_cache(self) -> bool:
        """Returns whether caching is enabled for this pipeline run.

        Returns:
            True if caching is enabled for this pipeline run.
        """
        enable_cache = self.pipeline_configuration["enable_cache"]
        return cast(bool, enable_cache)

    @property
    def zenml_version(self) -> Optional[str]:
        """Version of ZenML that this pipeline run was performed with.

        Returns:
            The version of ZenML that this pipeline run was performed with.
        """
        return self._model.zenml_version

    @property
    def git_sha(self) -> Optional[str]:
        """Git commit SHA that this pipeline run was performed on.

        This will only be set if the pipeline code is in a git repository and
        there are no dirty files when running the pipeline.

        Returns:
            The git commit SHA that this pipeline run was performed on.
        """
        return self._model.git_sha

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the pipeline run.

        Returns:
            The current status of the pipeline run.
        """
        # Query the run again since the status might have changed since this
        # object was created.
        return Client().get_pipeline_run(self.id).status

    @property
    def created(self) -> datetime:
        """Returns the creation time of the pipeline run.

        Returns:
            The creation time of the pipeline run.
        """
        return self._model.created

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

        assert self._model.id is not None
        steps = Client().zen_store.list_run_steps(self._model.id)
        self._steps = {step.name: StepView(step) for step in steps}

    def __repr__(self) -> str:
        """Returns a string representation of this pipeline run.

        Returns:
            A string representation of this pipeline run.
        """
        return (
            f"{self.__class__.__qualname__}(id={self.id}, "
            f"name='{self.name}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same pipeline run.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same pipeline run.
        """
        if isinstance(other, PipelineRunView):
            return self.id == other.id
        return NotImplemented
