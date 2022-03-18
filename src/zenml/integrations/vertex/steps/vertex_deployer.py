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
from zenml.environment import Environment
from zenml.integrations.vertex.services.vertex_deployment import (
    VertexDeploymentConfig,
    VertexDeploymentService,
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


class VertexDeployerConfig(BaseStepConfig):
    """Vertex model deployer step configuration

    Attributes:
        model_name: the name of the vertex model logged in the vertex artifact
            store for the current pipeline.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the vertex MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            vertex built-in scoring server will be used.
    """

    model_name: str = "model"
    workers: int = 1
    mlserver: bool = False


def vertex_deployer_step(
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
) -> Type[BaseStep]:
    """Shortcut function to create a pipeline step to deploy a given ML model
    on to Vertex AI.

    The returned step can be used in a pipeline to implement continuous
    deployment for an vertex model.

    Args:
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default
    Returns:
        A Vertex AI model deployer pipeline step.
    """

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    @step(enable_cache=enable_cache, name=name)
    def vertex_model_deployer(
        model: Model,
        deploy_decision: bool,
        config: VertexDeployerConfig,
        context: StepContext,
    ) -> VertexDeploymentService:
        """Vertex model deployer pipeline step

        Args:
            deploy_decision: whether to deploy the model or not
            config: configuration for the deployer step
            context: pipeline step context

        Returns:
            vertex deployment service
        """

        # Find a service created by a previous run of this step
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        last_service = cast(
            VertexDeploymentService,
            load_last_service_from_step(
                pipeline_name=step_env.pipeline_name,
                step_name=step_env.step_name,
                step_context=context,
            ),
        )
        if last_service and not isinstance(
            last_service, VertexDeploymentService
        ):
            raise ValueError(
                f"Last service deployed by step {step_env.step_name} and "
                f"pipeline {step_env.pipeline_name} has invalid type. Expected "
                f"VertexDeploymentService, found {type(last_service)}."
            )

        vertex_step_env = cast(
            VertexStepEnvironment, Environment()[VERTEX_STEP_ENVIRONMENT_NAME]
        )
        client = MlflowClient()
        # fetch the vertex artifacts logged during the pipeline run
        model_uri = None
        vertex_run = vertex_step_env.vertex_run
        if vertex_run and client.list_artifacts(
            vertex_run.info.run_id, config.model_name
        ):
            model_uri = get_artifact_uri(config.model_name)

        if not model_uri:
            # an vertex model was not found in the current run, so we simply reuse
            # the service created during the previous step run
            if not last_service:
                raise RuntimeError(
                    f"An vertex model with name `{config.model_name}` was not "
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
        predictor_cfg = VertexDeploymentConfig(
            model_name=config.model_name,
            model_uri=model_uri,
            workers=config.workers,
            mlserver=config.mlserver,
        )
        service = VertexDeploymentService(predictor_cfg)
        service.start(timeout=10)

        return service

    return vertex_model_deployer
