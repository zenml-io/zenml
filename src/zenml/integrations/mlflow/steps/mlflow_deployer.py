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

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.environment import Environment
from zenml.integrations.mlflow.mlflow_environment import (
    MLFLOW_STEP_ENVIRONMENT_NAME,
    MLFlowStepEnvironment,
)
from zenml.integrations.mlflow.mlflow_step_decorator import enable_mlflow
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentConfig,
    MLFlowDeploymentService,
)
from zenml.repository import Repository
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStep,
    BaseStepConfig,
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
        timeout: the number of seconds to wait for the service to start/stop.
    """

    model_name: str = "model"
    model_uri: str = ""
    workers: int = 1
    mlserver: bool = False
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT


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

    # check if an MLFlowModelDeployer stack component is registered with
    # the currently active stack
    mlflow_model_deployer_component = Repository().active_stack.model_deployer
    if not isinstance(mlflow_model_deployer_component, MLFlowModelDeployer):
        raise TypeError(
            "The active stack needs to have a model deployer component"
            "of type MLFlowModelDeployer registered for this step to work."
            "You can create a new stack with a MLFlowModelDeployer component"
            "or update your existing stack to add this component."
        )

    @enable_mlflow
    @step(enable_cache=enable_cache, name=name)
    def mlflow_model_deployer(
        deploy_decision: bool,
        model: ModelArtifact,
        config: MLFlowDeployerConfig,
    ) -> MLFlowDeploymentService:
        """MLflow model deployer pipeline step

        Args:
            deploy_decision: whether to deploy the model or not
            model: the model artifact to deploy
            config: configuration for the deployer step

        Returns:
            MLflow deployment service
        """

        if not config.model_uri:
            # fetch the MLflow artifacts logged during the pipeline run
            mlflow_step_env = cast(
                MLFlowStepEnvironment,
                Environment()[MLFLOW_STEP_ENVIRONMENT_NAME],
            )
            client = MlflowClient()
            model_uri = None
            mlflow_run = mlflow_step_env.mlflow_run
            if mlflow_run and client.list_artifacts(
                mlflow_run.info.run_id, config.model_name
            ):
                model_uri = get_artifact_uri(config.model_name)
            config.model_uri = model_uri

        # get pipeline name, step name and run id
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        pipeline_name = step_env.pipeline_name
        run_id = step_env.pipeline_run_id
        step_name = step_env.step_name

        # check if an MLFlowModelDeployer stack component is registered
        if not isinstance(mlflow_model_deployer_component, MLFlowModelDeployer):
            raise TypeError(
                "The active stack needs to have a model deployer component"
                "of type MLFlowModelDeployer registered for this step to work."
                "You can create a new stack with a MLFlowModelDeployer component"
                "or update your existing stack to add this component."
            )

        # fetch existing services with same pipeline name, step name and model name
        existing_services = mlflow_model_deployer_component.find_model_server(
            pipeline_name=pipeline_name,
            pipeline_step_name=step_name,
            model_name=config.model_name,
        )

        # create a config for the new model service
        predictor_cfg = MLFlowDeploymentConfig(
            model_name=config.model_name,
            model_uri=config.model_uri,
            workers=config.workers,
            mlserver=config.mlserver,
            pipeline_name=pipeline_name,
            pipeline_run_id=run_id,
            pipeline_step_name=step_name,
        )

        # check for conditions to deploy the model
        if not config.model_uri:
            # an MLflow model was not found in the current run, so we simply reuse
            # the service created during the previous step run
            if not existing_services:
                raise RuntimeError(
                    f"An MLflow model with name `{config.model_name}` was not "
                    f"trained in the current pipeline run and no previous "
                    f"service was found."
                )
            return existing_services[0]

        if not deploy_decision:
            if existing_services:
                return existing_services[0]
            else:
                # Returning a service with inactive state and status.
                return MLFlowDeploymentService(predictor_cfg)

        # create a new model deployment
        service = mlflow_model_deployer_component.deploy_model(
            replace=True,
            config=predictor_cfg,
            timeout=config.timeout,
        )
        return service

    return mlflow_model_deployer
