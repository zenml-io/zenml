#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the MLflow model deployer pipeline step."""

from typing import Optional, Type, cast

from mlflow.tracking import MlflowClient, artifact_utils

from zenml.client import Client
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.environment import Environment
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.mlflow_utils import (
    get_missing_mlflow_experiment_tracker_error,
)
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.logger import get_logger
from zenml.materializers import UnmaterializedArtifact
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseParameters,
    BaseStep,
    StepEnvironment,
    step,
)

logger = get_logger(__name__)


class MLFlowDeployerParameters(BaseParameters):
    """Model deployer step parameters for MLflow.

    Attributes:
        model_name: the name of the MLflow model logged in the MLflow artifact
            store for the current pipeline.
        experiment_name: Name of the MLflow experiment in which the model was
            logged.
        run_name: Name of the MLflow run in which the model was logged.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
        timeout: the number of seconds to wait for the service to start/stop.
    """

    model_name: str = "model"
    experiment_name: Optional[str] = None
    run_name: Optional[str] = None
    workers: int = 1
    mlserver: bool = False
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT


@step(enable_cache=False)
def mlflow_model_deployer_step(
    deploy_decision: bool,
    model: UnmaterializedArtifact,
    params: MLFlowDeployerParameters,
) -> MLFlowDeploymentService:
    """Model deployer pipeline step for MLflow.

    # noqa: DAR401

    Args:
        deploy_decision: whether to deploy the model or not
        model: the model artifact to deploy
        params: parameters for the deployer step

    Returns:
        MLflow deployment service
    """
    model_deployer = cast(
        MLFlowModelDeployer, MLFlowModelDeployer.get_active_model_deployer()
    )

    # fetch the MLflow artifacts logged during the pipeline run
    experiment_tracker = Client().active_stack.experiment_tracker

    if not isinstance(experiment_tracker, MLFlowExperimentTracker):
        raise get_missing_mlflow_experiment_tracker_error()

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    run_name = step_env.run_name
    step_name = step_env.step_name

    client = MlflowClient()
    mlflow_run_id = experiment_tracker.get_run_id(
        experiment_name=params.experiment_name or pipeline_name,
        run_name=params.run_name or run_name,
    )

    model_uri = ""
    if mlflow_run_id and client.list_artifacts(
        mlflow_run_id, params.model_name
    ):
        model_uri = artifact_utils.get_artifact_uri(
            run_id=mlflow_run_id, artifact_path=params.model_name
        )

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=params.model_name,
    )

    # create a config for the new model service
    predictor_cfg = MLFlowDeploymentConfig(
        model_name=params.model_name or "",
        model_uri=model_uri,
        workers=params.workers,
        mlserver=params.mlserver,
        pipeline_name=pipeline_name,
        pipeline_run_id=run_name,
        pipeline_step_name=step_name,
    )

    # Creating a new service with inactive state and status by default
    service = MLFlowDeploymentService(predictor_cfg)
    if existing_services:
        service = cast(MLFlowDeploymentService, existing_services[0])

    # check for conditions to deploy the model
    if not model_uri:
        # an MLflow model was not trained in the current run, so we simply reuse
        # the currently running service created for the same model, if any
        if not existing_services:
            logger.warning(
                f"An MLflow model with name `{params.model_name}` was not "
                f"logged in the current pipeline run and no running MLflow "
                f"model server was found. Please ensure that your pipeline "
                f"includes a step with a MLflow experiment configured that "
                "trains a model and logs it to MLflow. This could also happen "
                "if the current pipeline run did not log an MLflow model  "
                f"because the training step was cached."
            )
            # return an inactive service just because we have to return
            # something
            return service
        logger.info(
            f"An MLflow model with name `{params.model_name}` was not "
            f"trained in the current pipeline run. Reusing the existing "
            f"MLflow model server."
        )
        if not service.is_running:
            service.start(params.timeout)

        # return the existing service
        return service

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{params.model_name}'..."
        )
        # even when the deploy decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure
        # that a model server is available at all times
        if not service.is_running:
            service.start(params.timeout)
        return service

    # create a new model deployment and replace an old one if it exists
    new_service = cast(
        MLFlowDeploymentService,
        model_deployer.deploy_model(
            replace=True,
            config=predictor_cfg,
            timeout=params.timeout,
        ),
    )

    logger.info(
        f"MLflow deployment service started and reachable at:\n"
        f"    {new_service.prediction_url}\n"
    )

    return new_service


def mlflow_deployer_step(
    enable_cache: bool = True,
    name: Optional[str] = None,
) -> Type[BaseStep]:
    """Creates a pipeline step to deploy a given ML model with a local MLflow prediction server.

    The returned step can be used in a pipeline to implement continuous
    deployment for an MLflow model.

    Args:
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default
        name: Name of the step.

    Returns:
        an MLflow model deployer pipeline step
    """
    logger.warning(
        "The `mlflow_deployer_step` function is deprecated. Please "
        "use the built-in `mlflow_model_deployer_step` step instead."
    )
    return mlflow_model_deployer_step
