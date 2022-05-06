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

import os
from typing import cast

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.environment import Environment
from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
    DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    SeldonModelDeployer,
)
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentConfig,
    SeldonDeploymentService,
)
from zenml.io import fileio
from zenml.io import utils as io_utils
from zenml.logger import get_logger
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStepConfig,
    StepEnvironment,
    step,
)
from zenml.steps.step_context import StepContext

logger = get_logger(__name__)


class SeldonDeployerStepConfig(BaseStepConfig):
    """Seldon model deployer step configuration

    Attributes:
        service_config: Seldon Core deployment service configuration.
        secrets: a list of ZenML secrets containing additional configuration
            parameters for the Seldon Core deployment (e.g. credentials to
            access the Artifact Store where the models are stored). If supplied,
            the information fetched from these secrets is passed to the Seldon
            Core deployment server as a list of environment variables.
    """

    service_config: SeldonDeploymentConfig
    timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT


@step(enable_cache=False)
def seldon_model_deployer_step(
    deploy_decision: bool,
    config: SeldonDeployerStepConfig,
    context: StepContext,
    model: ModelArtifact,
) -> SeldonDeploymentService:
    """Seldon Core model deployer pipeline step

    This step can be used in a pipeline to implement continuous
    deployment for a ML model with Seldon Core.

    Args:
        deploy_decision: whether to deploy the model or not
        config: configuration for the deployer step
        model: the model artifact to deploy

    Returns:
        Seldon Core deployment service
    """
    model_deployer = SeldonModelDeployer.get_active_model_deployer()

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    pipeline_run_id = step_env.pipeline_run_id
    step_name = step_env.step_name

    # update the step configuration with the real pipeline runtime information
    config.service_config.pipeline_name = pipeline_name
    config.service_config.pipeline_run_id = pipeline_run_id
    config.service_config.pipeline_step_name = step_name

    def prepare_service_config(model_uri: str) -> SeldonDeploymentConfig:
        """Prepare the model files for model serving and create and return a
        Seldon service configuration for the model.

        This function ensures that the model files are in the correct format
        and file structure required by the Seldon Core server implementation
        used for model serving.

        Args:
            model_uri: the URI of the model artifact being served

        Returns:
            The URL to the model ready for serving.
        """
        served_model_uri = os.path.join(
            context.get_output_artifact_uri(), "seldon"
        )
        fileio.makedirs(served_model_uri)

        # TODO [ENG-773]: determine how to formalize how models are organized into
        #   folders and sub-folders depending on the model type/format and the
        #   Seldon Core protocol used to serve the model.

        # TODO [ENG-791]: auto-detect built-in Seldon server implementation
        #   from the model artifact type

        # TODO [ENG-792]: validate the model artifact type against the
        #   supported built-in Seldon server implementations
        if config.service_config.implementation == "TENSORFLOW_SERVER":
            # the TensorFlow server expects model artifacts to be
            # stored in numbered subdirectories, each representing a model
            # version
            io_utils.copy_dir(model_uri, os.path.join(served_model_uri, "1"))
        elif config.service_config.implementation == "SKLEARN_SERVER":
            # the sklearn server expects model artifacts to be
            # stored in a file called model.joblib
            model_uri = os.path.join(model.uri, "model")
            if not fileio.exists(model.uri):
                raise RuntimeError(
                    f"Expected sklearn model artifact was not found at "
                    f"{model_uri}"
                )
            fileio.copy(
                model_uri, os.path.join(served_model_uri, "model.joblib")
            )
        else:
            # default treatment for all other server implementations is to
            # simply reuse the model from the artifact store path where it
            # is originally stored
            served_model_uri = model_uri

        service_config = config.service_config.copy()
        service_config.model_uri = served_model_uri
        return service_config

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=config.service_config.model_name,
    )

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{config.service_config.model_name}'..."
        )
        service = cast(SeldonDeploymentService, existing_services[0])
        # even when the deploy decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if not service.is_running:
            service.start(timeout=config.timeout)
        return service

    # invoke the Seldon Core model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    service_config = prepare_service_config(model.uri)
    service = cast(
        SeldonDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=config.timeout
        ),
    )

    logger.info(
        f"Seldon deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
