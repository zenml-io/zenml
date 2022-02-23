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

from typing import Optional, Type, cast

from mlflow import get_artifact_uri  # type: ignore[import]
from mlflow.tracking import MlflowClient  # type: ignore[import]

from zenml.environment import Environment
from zenml.integrations.mlflow.mlflow_environment import (
    MLFLOW_STEP_ENVIRONMENT_NAME,
    MLFlowStepEnvironment,
)
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.services import load_last_service_from_step
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStep,
    BaseStepConfig,
    StepContext,
    StepEnvironment,
    step,
)


class MLFlowDeployerConfig(BaseStepConfig):
    """MLflow model deployer step configuration

    Attributes:
        model_name: the name of the MLflow model logged in the MLflow artifact
            store for the current pipeline.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
    """

    model_name: str = "model"
    workers: int = 1
    mlserver: bool = False


def mlflow_deployer_step(
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
) -> Type[BaseStep]:
    """Shortcut function to create a pipeline step to deploy a given ML model
    with a local MLflow prediction server.

    The returned step can be used in a pipeline to implement continuous
    deployment for an MLflow model.

    Args:
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default
    Returns:
        an MLflow model deployer pipeline step
    """

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    @enable_mlflow
    @step(enable_cache=enable_cache, name=name)
    def mlflow_model_deployer(
        deploy_decision: bool,
        config: MLFlowDeployerConfig,
        context: StepContext,
    ) -> MLFlowDeploymentService:
        """MLflow model deployer pipeline step

        Args:
            deploy_decision: whether to deploy the model or not
            config: configuration for the deployer step
            context: pipeline step context

        Returns:
            MLflow deployment service
        """

        # Find a service created by a previous run of this step
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        last_service = cast(
            MLFlowDeploymentService,
            load_last_service_from_step(
                pipeline_name=step_env.pipeline_name,
                step_name=step_env.step_name,
                step_context=context,
            ),
        )
        if last_service and not isinstance(
            last_service, MLFlowDeploymentService
        ):
            raise ValueError(
                f"Last service deployed by step {step_env.step_name} and "
                f"pipeline {step_env.pipeline_name} has invalid type. Expected "
                f"MLFlowDeploymentService, found {type(last_service)}."
            )

        mlflow_step_env = cast(
            MLFlowStepEnvironment, Environment()[MLFLOW_STEP_ENVIRONMENT_NAME]
        )
        client = MlflowClient()
        # fetch the MLflow artifacts logged during the pipeline run
        model_uri = None
        mlflow_run = mlflow_step_env.mlflow_run
        if mlflow_run and client.list_artifacts(
            mlflow_run.info.run_id, config.model_name
        ):
            model_uri = get_artifact_uri(config.model_name)

        if not model_uri:
            # an MLflow model was not found in the current run, so we simply reuse
            # the service created during the previous step run
            if not last_service:
                raise RuntimeError(
                    f"An MLflow model with name `{config.model_name}` was not "
                    f"trained in the current pipeline run and no previous "
                    f"service was found."
                )
            return last_service

        if not deploy_decision and last_service:
            return last_service

        # stop the service created during the last step run (will be replaced
        # by a new one to serve the new model)
        if last_service:
            last_service.stop(timeout=10)

        # create a new service for the new model
        predictor_cfg = MLFlowDeploymentConfig(
            model_name=config.model_name,
            model_uri=model_uri,
            workers=config.workers,
            mlserver=config.mlserver,
        )
        service = MLFlowDeploymentService(predictor_cfg)
        service.start(timeout=10)

        return service

    return mlflow_model_deployer
