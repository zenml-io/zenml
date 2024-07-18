"""Utility functions for running pipelines."""

import time
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple, Union
from uuid import UUID

from zenml import constants
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import ExecutionStatus, ModelStages
from zenml.logger import get_logger
from zenml.models import (
    FlavorFilter,
    PipelineDeploymentBase,
    PipelineDeploymentResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    StackResponse,
)
from zenml.new.pipelines.model_utils import NewModelRequest
from zenml.orchestrators.utils import get_run_name
from zenml.stack import Flavor, Stack
from zenml.utils import cloud_utils
from zenml.zen_stores.base_zen_store import BaseZenStore

if TYPE_CHECKING:
    from zenml.model.model import Model

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
    deployment: "PipelineDeploymentResponse",
) -> Optional["PipelineRunResponse"]:
    """Create a placeholder run for the deployment.

    If the deployment contains a schedule, no placeholder run will be
    created.

    Args:
        deployment: The deployment for which to create the placeholder run.

    Returns:
        The placeholder run or `None` if no run was created.
    """
    assert deployment.user

    if deployment.schedule:
        return None

    run_request = PipelineRunRequest(
        name=get_run_name(run_name_template=deployment.run_name_template),
        # We set the start time on the placeholder run already to
        # make it consistent with the {time} placeholder in the
        # run name. This means the placeholder run will usually
        # have longer durations than scheduled runs, as for them
        # the start_time is only set once the first step starts
        # running.
        start_time=datetime.utcnow(),
        orchestrator_run_id=None,
        user=deployment.user.id,
        workspace=deployment.workspace.id,
        deployment=deployment.id,
        pipeline=deployment.pipeline.id if deployment.pipeline else None,
        status=ExecutionStatus.INITIALIZING,
    )
    return Client().zen_store.create_run(run_request)


def get_placeholder_run(
    deployment_id: UUID,
) -> Optional["PipelineRunResponse"]:
    """Get the placeholder run for a deployment.

    Args:
        deployment_id: ID of the deployment for which to get the placeholder
            run.

    Returns:
        The placeholder run or `None` if there exists no placeholder run for the
        deployment.
    """
    runs = Client().list_pipeline_runs(
        sort_by="asc:created",
        size=1,
        deployment_id=deployment_id,
        status=ExecutionStatus.INITIALIZING,
    )
    if len(runs.items) == 0:
        return None

    run = runs.items[0]
    if run.orchestrator_run_id is None:
        return run

    return None


def deploy_pipeline(
    deployment: "PipelineDeploymentResponse",
    stack: "Stack",
    placeholder_run: Optional["PipelineRunResponse"] = None,
) -> None:
    """Run a deployment.

    Args:
        deployment: The deployment to run.
        stack: The stack on which to run the deployment.
        placeholder_run: An optional placeholder run for the deployment. This
            will be deleted in case the pipeline deployment failed.

    Raises:
        Exception: Any exception that happened while deploying or running
            (in case it happens synchronously) the pipeline.
    """
    stack.prepare_pipeline_deployment(deployment=deployment)

    # Prevent execution of nested pipelines which might lead to
    # unexpected behavior
    previous_value = constants.SHOULD_PREVENT_PIPELINE_EXECUTION
    constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True
    try:
        stack.deploy_pipeline(deployment=deployment)
    except Exception as e:
        if (
            placeholder_run
            and Client().get_pipeline_run(placeholder_run.id).status
            == ExecutionStatus.INITIALIZING
        ):
            # The run hasn't actually started yet, which means that we
            # failed during initialization -> We don't want the
            # placeholder run to stay in the database
            Client().delete_pipeline_run(placeholder_run.id)

        raise e
    finally:
        constants.SHOULD_PREVENT_PIPELINE_EXECUTION = previous_value


def _update_new_requesters(
    requester_name: str,
    model: "Model",
    new_versions_requested: Dict[Tuple[str, Optional[str]], NewModelRequest],
    other_models: Set["Model"],
) -> None:
    key = (
        model.name,
        str(model.version) if model.version else None,
    )
    if model.version is None:
        version_existed = False
    else:
        try:
            model._get_model_version()
            version_existed = key not in new_versions_requested
        except KeyError as e:
            if model.version in ModelStages.values():
                raise KeyError(
                    f"Unable to get model `{model.name}` using stage "
                    f"`{model.version}`, please check that the model "
                    "version in given stage exists before running a pipeline."
                ) from e
            version_existed = False
    if not version_existed:
        model.was_created_in_this_run = True
        new_versions_requested[key].update_request(
            model,
            NewModelRequest.Requester(source="step", name=requester_name),
        )
    else:
        other_models.add(model)


def prepare_model_versions(
    deployment: Union["PipelineDeploymentBase", "PipelineDeploymentResponse"],
) -> None:
    """Create model versions which are missing and validate existing ones that are used in the pipeline run.

    Args:
        deployment: The pipeline deployment configuration.
    """
    new_versions_requested: Dict[
        Tuple[str, Optional[str]], NewModelRequest
    ] = defaultdict(NewModelRequest)
    other_models: Set["Model"] = set()
    all_steps_have_own_config = True
    for step in deployment.step_configurations.values():
        step_model = step.config.model
        all_steps_have_own_config = (
            all_steps_have_own_config and step.config.model is not None
        )
        if step_model:
            _update_new_requesters(
                model=step_model,
                requester_name=step.config.name,
                new_versions_requested=new_versions_requested,
                other_models=other_models,
            )
    if not all_steps_have_own_config:
        pipeline_model = deployment.pipeline_configuration.model
        if pipeline_model:
            _update_new_requesters(
                model=pipeline_model,
                requester_name=deployment.pipeline_configuration.name,
                new_versions_requested=new_versions_requested,
                other_models=other_models,
            )
    elif deployment.pipeline_configuration.model is not None:
        logger.warning(
            f"ModelConfig of pipeline `{deployment.pipeline_configuration.name}` is overridden in all "
            f"steps. "
        )

    _validate_new_version_requests(new_versions_requested)

    for other_model in other_models:
        other_model._validate_config_in_runtime()


def _validate_new_version_requests(
    new_versions_requested: Dict[Tuple[str, Optional[str]], NewModelRequest],
) -> None:
    """Validate the model version that are used in the pipeline run.

    Args:
        new_versions_requested: A dict of new model version request objects.

    """
    is_cloud_model = True
    for key, data in new_versions_requested.items():
        model_name, model_version = key
        if len(data.requesters) > 1:
            logger.warning(
                f"New version of model version `{model_name}::{model_version or 'NEW'}` "
                f"requested in multiple decorators:\n{data.requesters}\n We recommend "
                "that `Model` requesting new version is configured only in one "
                "place of the pipeline."
            )
        model_version_response = data.model._validate_config_in_runtime()
        is_cloud_model &= cloud_utils.is_cloud_model_version(
            model_version_response
        )
    if not is_cloud_model:
        logger.info(
            "Models can be viewed in the dashboard using ZenML Pro. Sign up "
            "for a free trial at https://www.zenml.io/cloud/"
        )


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
            FlavorFilter(name=component.flavor, type=component.type)
        )
        assert len(flavors) == 1
        flavor_model = flavors[0]

        if flavor_model.workspace is not None:
            raise ValueError("No custom stack component flavors allowed.")

        flavor = Flavor.from_model(flavor_model)
        component_config = flavor.config_class(**component.configuration)

        if component_config.is_local:
            raise ValueError("No local stack components allowed.")


def validate_run_config_is_runnable_from_server(
    run_configuration: "PipelineRunConfiguration",
) -> None:
    """Validates that the run configuration can be used to run from the server.

    Args:
        run_configuration: The run configuration to validate.

    Raises:
        ValueError: If there are values in the run configuration that are not
            allowed when running a pipeline from the server.
    """
    if run_configuration.parameters:
        raise ValueError(
            "Can't set parameters when running pipeline via Rest API."
        )

    if run_configuration.build:
        raise ValueError("Can't set build when running pipeline via Rest API.")

    if run_configuration.schedule:
        raise ValueError(
            "Can't set schedule when running pipeline via Rest API."
        )

    if run_configuration.settings.get("docker"):
        raise ValueError(
            "Can't set DockerSettings when running pipeline via Rest API."
        )

    for step_update in run_configuration.steps.values():
        if step_update.settings.get("docker"):
            raise ValueError(
                "Can't set DockerSettings when running pipeline via Rest API."
            )
