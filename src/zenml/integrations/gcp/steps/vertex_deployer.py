#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the Vertex model deployer pipeline step."""

from typing import Optional, cast

from mlflow.tracking import MlflowClient, artifact_utils

from zenml import get_step_context, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.client import Client
from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
)
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def vertex_model_deployer_step(
    model: UnmaterializedArtifact,
    deploy_decision: bool = True,
    experiment_name: Optional[str] = None,
    run_name: Optional[str] = None,
    model_name: str = "model",
    workers: int = 1,
    mlserver: bool = False,
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
) -> Optional[MLFlowDeploymentService]:
    """Model deployer pipeline step for Vertex.

    This step deploys a model logged in the MLflow artifact store to a
    deployment service. The user would typically use this step in a pipeline
    that deploys a model that was already registered in the MLflow model
    registr either manually or by using the `mlflow_model_registry_step`.

    Args:
        deploy_decision: whether to deploy the model or not
        model: the model artifact to deploy
        experiment_name: Name of the MLflow experiment in which the model was
            logged.
        run_name: Name of the MLflow run in which the model was logged.
        model_name: the name of the MLflow model logged in the MLflow artifact
            store for the current pipeline.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
        timeout: the number of seconds to wait for the service to start/stop.

    Returns:
        MLflow deployment service or None if no service was deployed or found

    Raises:
        ValueError: if the MLflow experiment tracker is not found
    """
    model_deployer = cast(
        MLFlowModelDeployer, MLFlowModelDeployer.get_active_model_deployer()
    )

    experiment_tracker = Client().active_stack.experiment_tracker

    if not isinstance(experiment_tracker, MLFlowExperimentTracker):
        raise ValueError(
            "MLflow model deployer step requires an MLflow experiment "
            "tracker. Please add an MLflow experiment tracker to your "
            "stack."
        )

    # get pipeline name, step name and run id
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    run_name = step_context.pipeline_run.name
    step_name = step_context.step_run.name

    # Configure Mlflow so the client points to the correct store
    experiment_tracker.configure_mlflow()
    client = MlflowClient()
    mlflow_run_id = experiment_tracker.get_run_id(
        experiment_name=experiment_name or pipeline_name,
        run_name=run_name or run_name,
    )

    # Fetch the model URI from the MLflow artifact store
    model_uri = ""
    if mlflow_run_id and client.list_artifacts(mlflow_run_id, model_name):
        model_uri = artifact_utils.get_artifact_uri(
            run_id=mlflow_run_id, artifact_path=model_name
        )

    # Fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=model_name,
    )

    # Check whether to deploy a new service
    if model_uri and deploy_decision:
        predictor_cfg = MLFlowDeploymentConfig(
            model_name=model_name or "",
            model_uri=model_uri,
            workers=workers,
            mlserver=mlserver,
            pipeline_name=pipeline_name,
            run_name=run_name,
            pipeline_run_id=run_name,
            pipeline_step_name=step_name,
            timeout=timeout,
        )
        new_service = cast(
            MLFlowDeploymentService,
            model_deployer.deploy_model(
                replace=True,
                config=predictor_cfg,
                timeout=timeout,
            ),
        )
        logger.info(
            f"MLflow deployment service started and reachable at:\n"
            f"    {new_service.prediction_url}\n"
        )
        logger.info("Stopping existing services...")
        for existing_service in existing_services:
            existing_service.stop(timeout)
        return new_service

    # Check whether an existing service can be reused
    elif existing_services:
        if not model_uri:
            logger.info(
                f"Skipping model deployment because an MLflow model with name "
                f" `{model_name}` was not trained in the current pipeline run."
            )
        elif not deploy_decision:
            logger.info(
                "Skipping model deployment because the deployment decision "
                "was negative."
            )
        logger.info(
            f"Reusing last model server deployed by step '{step_name}' of "
            f"pipeline '{pipeline_name}' for model '{model_name}'..."
        )
        service = cast(MLFlowDeploymentService, existing_services[0])
        if not service.is_running:
            service.start(timeout)
        return service

    # Log a warning if no service was deployed or found
    elif deploy_decision and not model_uri:
        logger.warning(
            f"An MLflow model with name `{model_name}` was not "
            f"logged in the current pipeline run and no running MLflow "
            f"model server was found. Please ensure that your pipeline "
            f"includes a step with an MLflow experiment configured that "
            "trains a model and logs it to MLflow. This could also happen "
            "if the current pipeline run did not log an MLflow model  "
            f"because the training step was cached."
        )
    return None
