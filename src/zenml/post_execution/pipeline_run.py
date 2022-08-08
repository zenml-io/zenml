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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ml_metadata import proto

from zenml.enums import ExecutionStatus
from zenml.logger import get_apidocs_link, get_logger
from zenml.post_execution.step import StepView
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

if TYPE_CHECKING:
    from zenml.metadata_stores import BaseMetadataStore

logger = get_logger(__name__)


class PipelineRunView:
    """Post-execution pipeline run class.

    This can be used to query steps and artifact information associated with a
    pipeline execution.
    """

    def __init__(
        self,
        id_: int,
        name: str,
        executions: List[proto.Execution],
        metadata_store: "BaseMetadataStore",
    ):
        """Initializes a post-execution pipeline run object.

        In most cases `PipelineRunView` objects should not be created manually
        but retrieved from a `PipelineView` object instead.

        Args:
            id_: The context id of this pipeline run.
            name: The name of this pipeline run.
            executions: All executions associated with this pipeline run.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this pipeline run.
        """
        self._id = id_
        self._name = name
        self._metadata_store = metadata_store

        self._executions = executions
        self._steps: Dict[str, StepView] = OrderedDict()

        # This might be set from the parent pipeline view in case this run
        # is also tracked in the ZenStore
        self._run_wrapper: Optional[PipelineRunWrapper] = None

    @property
    def name(self) -> str:
        """Returns the name of the pipeline run.

        Returns:
            The name of the pipeline run.
        """
        return self._name

    @property
    def zenml_version(self) -> Optional[str]:
        """Version of ZenML that this pipeline run was performed with.

        Returns:
            The version of ZenML that this pipeline run was performed with.
        """
        if self._run_wrapper:
            return self._run_wrapper.zenml_version
        return None

    @property
    def git_sha(self) -> Optional[str]:
        """Git commit SHA that this pipeline run was performed on.

        This will only be set if the pipeline code is in a git repository and
        there are no dirty files when running the pipeline.

        Returns:
            The git commit SHA that this pipeline run was performed on.
        """
        if self._run_wrapper:
            return self._run_wrapper.git_sha
        return None

    @property
    def runtime_configuration(self) -> Optional["RuntimeConfiguration"]:
        """Runtime configuration that was used for this pipeline run.

        This will only be set if the pipeline run was tracked in a ZenStore.

        Returns:
            The runtime configuration that was used for this pipeline run.
        """
        if self._run_wrapper:
            return RuntimeConfiguration(
                **self._run_wrapper.runtime_configuration
            )

        return None

    @property
    def status(self) -> ExecutionStatus:
        """Returns the current status of the pipeline run.

        Returns:
            The current status of the pipeline run.
        """
        step_statuses = (step.status for step in self.steps)

        if any(status == ExecutionStatus.FAILED for status in step_statuses):
            return ExecutionStatus.FAILED
        elif all(
            status == ExecutionStatus.COMPLETED
            or status == ExecutionStatus.CACHED
            for status in step_statuses
        ):
            return ExecutionStatus.COMPLETED
        else:
            return ExecutionStatus.RUNNING

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
            "post_execution",
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

        self._steps = self._metadata_store.get_pipeline_run_steps(self)

        if self._run_wrapper:
            # If we have the run wrapper from the ZenStore, pass on the step
            # wrapper so users can access additional information about the step.
            for step_wrapper in self._run_wrapper.pipeline.steps:
                if step_wrapper.name in self._steps:
                    self._steps[step_wrapper.name]._step_wrapper = step_wrapper

    def __repr__(self) -> str:
        """Returns a string representation of this pipeline run.

        Returns:
            A string representation of this pipeline run.
        """
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"name='{self._name}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same pipeline run.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same pipeline run.
        """
        if isinstance(other, PipelineRunView):
            return (
                self._id == other._id
                and self._metadata_store.uuid == other._metadata_store.uuid
            )
        return NotImplemented
