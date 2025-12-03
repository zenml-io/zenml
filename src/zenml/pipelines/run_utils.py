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
"""Utility functions for running pipelines."""

import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.models import (
    FlavorFilter,
    LogsRequest,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunTriggerInfo,
    PipelineSnapshotBase,
    PipelineSnapshotResponse,
    StackResponse,
)
from zenml.stack import Flavor, Stack
from zenml.utils import (
    code_utils,
    notebook_utils,
    source_utils,
    string_utils,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore

if TYPE_CHECKING:
    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)


def get_default_run_name(pipeline_name: str) -> str:
    """Gets the default name for a pipeline run.

    Args:
        pipeline_name: Name of the pipeline which will be run.

    Returns:
        Run name.
    """
    return f"{pipeline_name}-{{date}}-{{time}}"


def create_placeholder_run(
    snapshot: "PipelineSnapshotResponse",
    orchestrator_run_id: Optional[str] = None,
    logs: Optional["LogsRequest"] = None,
    trigger_info: Optional[PipelineRunTriggerInfo] = None,
) -> "PipelineRunResponse":
    """Create a placeholder run for the snapshot.

    Args:
        snapshot: The snapshot for which to create the placeholder run.
        orchestrator_run_id: The orchestrator run ID for the run.
        logs: The logs for the run.
        trigger_info: The trigger information for the run.

    Returns:
        The placeholder run.
    """
    start_time = utc_now()
    run_request = PipelineRunRequest(
        name=string_utils.format_name_template(
            name_template=snapshot.run_name_template,
            substitutions=snapshot.pipeline_configuration.finalize_substitutions(
                start_time=start_time,
            ),
        ),
        # We set the start time on the placeholder run already to
        # make it consistent with the {time} placeholder in the
        # run name. This means the placeholder run will usually
        # have longer durations than scheduled runs, as for them
        # the start_time is only set once the first step starts
        # running.
        start_time=start_time,
        orchestrator_run_id=orchestrator_run_id,
        project=snapshot.project_id,
        snapshot=snapshot.id,
        pipeline=snapshot.pipeline.id if snapshot.pipeline else None,
        status=ExecutionStatus.INITIALIZING,
        tags=snapshot.pipeline_configuration.tags,
        logs=logs,
        trigger_info=trigger_info,
    )
    run, _ = Client().zen_store.get_or_create_run(run_request)
    return run


def wait_for_pipeline_run_to_finish(run_id: UUID) -> "PipelineRunResponse":
    """Waits until a pipeline run is finished.

    Args:
        run_id: ID of the run for which to wait.

    Returns:
        Model of the finished run.
    """
    sleep_interval = 1
    max_sleep_interval = 64

    while True:
        run = Client().get_pipeline_run(run_id)

        if run.status.is_finished:
            return run

        logger.info(
            "Waiting for pipeline run with ID %s to finish (current status: %s)",
            run_id,
            run.status,
        )
        time.sleep(sleep_interval)
        if sleep_interval < max_sleep_interval:
            sleep_interval *= 2


def validate_stack_is_runnable_from_server(
    zen_store: BaseZenStore, stack: StackResponse
) -> None:
    """Validate if a stack model is runnable from the server.

    Args:
        zen_store: ZenStore to use for listing flavors.
        stack: The stack to validate.

    Raises:
        ValueError: If the stack has components of a custom flavor or local
            components.
    """
    for component_list in stack.components.values():
        assert len(component_list) == 1
        component = component_list[0]
        flavors = zen_store.list_flavors(
            FlavorFilter(name=component.flavor_name, type=component.type)
        )
        assert len(flavors) == 1
        flavor_model = flavors[0]

        if flavor_model.is_custom:
            raise ValueError(
                "Unable to run pipeline from the server on a stack that "
                "includes stack components with a custom flavor."
            )

        flavor = Flavor.from_model(flavor_model)
        component_config = flavor.config_class(**component.configuration)

        if component_config.is_local:
            raise ValueError(
                "Unable to run pipeline from the server on a stack that "
                "includes local stack components."
            )


def validate_run_config_is_runnable_from_server(
    run_configuration: "PipelineRunConfiguration",
    is_dynamic: bool,
) -> None:
    """Validates that the run configuration can be used to run from the server.

    Args:
        run_configuration: The run configuration to validate.
        is_dynamic: Whether the snapshot to run is dynamic.

    Raises:
        ValueError: If there are values in the run configuration that are not
            allowed when running a pipeline from the server.
    """
    if run_configuration.parameters and not is_dynamic:
        raise ValueError(
            "Can't set pipeline parameters when running a static pipeline via "
            "the REST API. You can either use dynamic pipelines for which you "
            "can pass pipeline parameters, or refactore your pipeline code to "
            "use step parameters instead of pipeline parameters. For example, "
            "instead of: "
            "```yaml "
            "parameters: "
            "  param1: 1 "
            "  param2: 2 "
            "``` "
            "You'll need to modify your pipeline code to pass parameters "
            "directly to steps: "
            "```yaml "
            "steps: "
            "  step1: "
            "    parameters: "
            "      param1: 1 "
            "      param2: 2 "
            "``` "
        )

    if run_configuration.build:
        raise ValueError("Can't set build when running pipeline via Rest API.")

    if run_configuration.schedule:
        raise ValueError(
            "Can't set schedule when running pipeline via Rest API."
        )

    if run_configuration.settings and run_configuration.settings.get("docker"):
        raise ValueError(
            "Can't set DockerSettings when running pipeline via Rest API."
        )

    if run_configuration.steps:
        for step_update in run_configuration.steps.values():
            if step_update.settings and step_update.settings.get("docker"):
                raise ValueError(
                    "Can't set DockerSettings when running pipeline via "
                    "Rest API."
                )


def upload_notebook_cell_code_if_necessary(
    snapshot: "PipelineSnapshotBase", stack: "Stack"
) -> None:
    """Upload notebook cell code if necessary.

    This function checks if any of the steps of the pipeline that will be
    executed in a different process are defined in a notebook. If that is the
    case, it will extract that notebook cell code into python files and upload
    an archive of all the necessary files to the artifact store.

    Args:
        snapshot: The snapshot.
        stack: The stack on which the snapshot will happen.

    Raises:
        RuntimeError: If the code for one of the steps that will run out of
            process cannot be extracted into a python file.
    """
    should_upload = False
    resolved_notebook_sources = source_utils.get_resolved_notebook_sources()

    for step in snapshot.step_configurations.values():
        source = step.spec.source

        if source.type == SourceType.NOTEBOOK:
            if (
                stack.orchestrator.flavor != "local"
                or step.config.step_operator
            ):
                should_upload = True
                cell_code = resolved_notebook_sources.get(
                    source.import_path, None
                )

                # Code does not run in-process, which means we need to
                # extract the step code into a python file
                if not cell_code:
                    raise RuntimeError(
                        f"Unable to run step {step.config.name}. This step is "
                        "defined in a notebook and you're trying to run it "
                        "in a remote environment, but ZenML was not able to "
                        "detect the step code in the notebook. To fix "
                        "this error, define your step in a python file instead "
                        "of a notebook."
                    )

    if should_upload:
        logger.info("Uploading notebook code...")

        for _, cell_code in resolved_notebook_sources.items():
            notebook_utils.warn_about_notebook_cell_magic_commands(
                cell_code=cell_code
            )
            module_name = notebook_utils.compute_cell_replacement_module_name(
                cell_code=cell_code
            )
            file_name = f"{module_name}.py"

            code_utils.upload_notebook_code(
                artifact_store=stack.artifact_store,
                cell_code=cell_code,
                file_name=file_name,
            )

        all_snapshot_sources = get_all_sources_from_value(snapshot)

        for source in all_snapshot_sources:
            if source.type == SourceType.NOTEBOOK:
                setattr(source, "artifact_store_id", stack.artifact_store.id)

        logger.info("Upload finished.")


def get_all_sources_from_value(value: Any) -> List[Source]:
    """Get all source objects from a value.

    Args:
        value: The value from which to get all the source objects.

    Returns:
        List of source objects for the given value.
    """
    sources = []
    if isinstance(value, Source):
        sources.append(value)
    elif isinstance(value, BaseModel):
        for v in value.__dict__.values():
            sources.extend(get_all_sources_from_value(v))
    elif isinstance(value, Dict):
        for v in value.values():
            sources.extend(get_all_sources_from_value(v))
    elif isinstance(value, (List, Set, tuple)):
        for v in value:
            sources.extend(get_all_sources_from_value(v))

    return sources
