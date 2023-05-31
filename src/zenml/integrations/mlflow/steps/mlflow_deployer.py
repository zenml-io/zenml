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

from typing import Any, Optional, cast

from zenml import step
from zenml.client import Client
from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    MLFLOW_MODEL_FORMAT,
)
from zenml.environment import Environment
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
    ModelVersionStage,
)
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    StepEnvironment,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def mlflow_model_deployer_step(
    model: Any,
    deploy_decision: bool = True,
    experiment_name: Optional[str] = None,
    run_name: Optional[str] = None,
    model_name: str = "model",
    workers: int = 1,
    mlserver: bool = False,
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
) -> MLFlowDeploymentService:
    """Model deployer pipeline step for MLflow.

    This step deploys a model logged in the MLflow artifact store to a
    deployment service. The user would typically use this step in a pipeline
    that deploys a model that was already registered in the MLflow model
    registr either manually or by using the `mlflow_model_registry_step`.

    Args:
        model: the model to deploy
        deploy_decision: whether to deploy the model or not
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
        MLflow deployment service
    """
    model_deployer = cast(
        MLFlowModelDeployer, MLFlowModelDeployer.get_active_model_deployer()
    )

    # get the pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    experiment_name = experiment_name or pipeline_name
    run_name = run_name or step_env.run_name
    step_name = step_env.step_name

    # find or log the model in MLflow
    model_uri = model_deployer.find_or_log_mlflow_model(
        model=model,
        model_name=model_name,
        experiment_name=experiment_name,
        run_name=run_name,
    )

    # Create a config for the new model service
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

    # Create or replace the service if the user wants to deploy
    if deploy_decision:
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
        return new_service

    logger.info("Skipping model deployment.")

    # Else try to resume a service with same pipeline, step, and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=model_name,
    )
    if existing_services:
        logger.info(
            f"Reusing last model server deployed by step '{step_name}' and "
            f"pipeline '{pipeline_name}' for model '{model_name}'..."
        )
        service = cast(MLFlowDeploymentService, existing_services[0])
        if not service.is_running:
            service.start(timeout)
        return service

    return MLFlowDeploymentService(predictor_cfg)


@step(enable_cache=False)
def mlflow_model_registry_deployer_step(
    registry_model_name: str,
    registry_model_version: Optional[str] = None,
    registry_model_stage: Optional[ModelVersionStage] = None,
    replace_existing: bool = True,
    model_name: str = "model",
    workers: int = 1,
    mlserver: bool = False,
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT,
) -> MLFlowDeploymentService:
    """Model deployer pipeline step for MLflow.

    Args:
        registry_model_name: the name of the model in the model registry
        registry_model_version: the version of the model in the model registry
        registry_model_stage: the stage of the model in the model registry
        replace_existing: Whether to create a new deployment service or not
        model_name: the name of the MLflow model logged in the MLflow artifact
            store for the current pipeline.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
        timeout: the number of seconds to wait for the service to start/stop.

    Returns:
        MLflow deployment service

    Raises:
        ValueError: if neither registry_model_version nor registry_model_stage
            is not provided
        ValueError: if No MLflow experiment tracker is found in the current
            active stack
        LookupError: if no model version is found in the MLflow model registry.
    """
    if not registry_model_version and not registry_model_stage:
        raise ValueError(
            "Either registry_model_version or registry_model_stage must"
            "be provided in addition to registry_model_name to the MLflow"
            "model registry deployer step. Since the"
            "mlflow_model_registry_deployer_step is used in conjunction with"
            "the mlflow_model_registry."
        )

    model_deployer = cast(
        MLFlowModelDeployer, MLFlowModelDeployer.get_active_model_deployer()
    )

    # fetch the MLflow model registry
    model_registry = Client().active_stack.model_registry
    if not isinstance(model_registry, MLFlowModelRegistry):
        raise ValueError(
            "The MLflow model registry step can only be used with an "
            "MLflow model registry."
        )

    # fetch the model version
    model_version = None
    if registry_model_version:
        try:
            model_version = model_registry.get_model_version(
                name=registry_model_name,
                version=registry_model_version,
            )
        except KeyError:
            model_version = None
    elif registry_model_stage:
        model_version = model_registry.get_latest_model_version(
            name=registry_model_name,
            stage=registry_model_stage,
        )
    if not model_version:
        raise LookupError(
            f"No Model Version found for model name "
            f"{registry_model_name} and version "
            f"{registry_model_version} or stage "
            f"{registry_model_stage}"
        )
    if model_version.model_format != MLFLOW_MODEL_FORMAT:
        raise ValueError(
            f"Model version {model_version.version} of model "
            f"{model_version.registered_model.name} is not an MLflow model."
            f"Only MLflow models can be deployed with the MLflow deployer "
            f"using this step."
        )
    # fetch existing services with same pipeline name, step name and model name
    existing_services = (
        model_deployer.find_model_server(
            registry_model_name=model_version.registered_model.name,
        )
        if replace_existing
        else None
    )

    # create a config for the new model service
    metadata = model_version.metadata or ModelRegistryModelMetadata()
    predictor_cfg = MLFlowDeploymentConfig(
        model_name=model_name or "",
        model_uri=model_version.model_source_uri,
        registry_model_name=model_version.registered_model.name,
        registry_model_version=model_version.version,
        registry_model_stage=model_version.stage.value,
        workers=workers,
        mlserver=mlserver,
        pipeline_name=metadata.zenml_pipeline_name or "",
        run_name=metadata.zenml_run_name or "",
        pipeline_step_name=metadata.zenml_step_name or "",
        timeout=timeout,
    )

    # Creating a new service with inactive state and status by default
    service = MLFlowDeploymentService(predictor_cfg)
    if existing_services:
        service = cast(MLFlowDeploymentService, existing_services[0])

    # check if the model is already deployed but not running
    if existing_services and not service.is_running:
        service.start(timeout)
        return service

    # create a new model deployment and replace an old one if it exists
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

    return new_service
