"""Utility functions for running pipelines."""

from collections import defaultdict
from datetime import datetime
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from zenml import constants
from zenml.client import Client
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import ExecutionStatus, ModelStages
from zenml.logger import get_logger
from zenml.models import (
    PipelineDeploymentBase,
    PipelineDeploymentResponse,
    PipelineRunRequest,
    PipelineRunResponse,
)
from zenml.new.pipelines.model_utils import NewModelRequest
from zenml.orchestrators.utils import get_run_name
from zenml.stack import Stack
from zenml.utils import cloud_utils

if TYPE_CHECKING:
    from zenml.config.source import Source
    from zenml.model.model import Model

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]
    HookSpecification = Union[str, "Source", FunctionType]

logger = get_logger(__name__)


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
