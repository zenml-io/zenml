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
"""Implementation of the Seldon Deployer step."""

import os
from typing import Optional, cast

from zenml.environment import Environment
from zenml.integrations.seldon_v2.model_deployers.seldon_v2_model_deployer import (
    DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT,
    SeldonV2ModelDeployer,
)
from zenml.integrations.seldon_v2.services.seldon_deployment import (
    SeldonV2ModelConfig,
    SeldonV2ModelService,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers import UnmaterializedArtifact
from zenml.model_registries.base_model_registry import ModelVersionStage
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseParameters,
    StepEnvironment,
    step,
)
from zenml.steps.step_context import StepContext
from zenml.utils import io_utils

logger = get_logger(__name__)


class SeldonV2DeployerStepParameters(BaseParameters):
    """Seldon model deployer step parameters.

    Attributes:
        service_config: Seldon Core V2 model service configuration.
        registry_name: name of the model in the model registry
        registry_model_version: version of the model in the model registry
        registry_model_stage: stage of the model in the model registry
        replace_existing: whether to replace an existing deployment of the
            model with the same name, this is used only when the model is
            deployed from a model registry stored model.
    """

    service_config: SeldonV2ModelConfig
    registry_name: Optional[str] = None
    registry_model_version: Optional[str] = None
    registry_model_stage: Optional[ModelVersionStage] = None
    replace_existing: bool = True
    timeout: int = DEFAULT_SELDON_V2_MODEL_START_STOP_TIMEOUT


@step(enable_cache=False)
def seldon_v2_model_deployer_step(
    deploy_decision: bool,
    params: SeldonV2DeployerStepParameters,
    context: StepContext,
    model: UnmaterializedArtifact,
) -> SeldonV2ModelService:
    """Seldon Core V2 model deployer pipeline step.

    This step can be used in a pipeline to implement continuous
    deployment for a ML model with Seldon Core.

    Args:
        deploy_decision: whether to deploy the model or not
        params: parameters for the deployer step
        model: the model artifact to deploy
        context: the step context

    Returns:
        Seldon Core deployment service
    """
    model_deployer = cast(
        SeldonV2ModelDeployer,
        SeldonV2ModelDeployer.get_active_model_deployer(),
    )

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    run_name = step_env.run_name
    step_name = step_env.step_name

    # update the step configuration with the real pipeline runtime information
    params.service_config.pipeline_name = pipeline_name
    params.service_config.run_name = run_name
    params.service_config.pipeline_step_name = step_name

    def prepare_service_config(model_uri: str) -> SeldonV2ModelConfig:
        """Prepare the model files for model serving.

        This creates and returns a Seldon service configuration for the model.

        This function ensures that the model files are in the correct format
        and file structure required by the Seldon Core server requirements
        used for model serving.

        Args:
            model_uri: the URI of the model artifact being served

        Returns:
            The URL to the model ready for serving.

        Raises:
            RuntimeError: if the model files were not found
        """
        served_model_uri = os.path.join(
            context.get_output_artifact_uri(), "seldon"
        )
        fileio.makedirs(served_model_uri)

        # TODO [ENG-773]: determine how to formalize how models are organized into
        #   folders and sub-folders depending on the model type/format and the
        #   Seldon Core protocol used to serve the model.

        # TODO [ENG-791]: auto-detect built-in Seldon server requirements
        #   from the model artifact type

        # TODO [ENG-792]: validate the model artifact type against the
        #   supported built-in Seldon server requirementss
        if "tensorflow" in params.service_config.requirements:
            # the TensorFlow server expects model artifacts to be
            # stored in numbered subdirectories, each representing a model
            # version
            io_utils.copy_dir(model_uri, os.path.join(served_model_uri, "1"))
        elif "sklearn" in params.service_config.requirements:
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
            # default treatment for all other server requirementss is to
            # simply reuse the model from the artifact store path where it
            # is originally stored
            served_model_uri = model_uri

        service_config = params.service_config.copy()
        service_config.model_uri = served_model_uri
        return service_config

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=params.service_config.name,
    )

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{params.service_config.name}'..."
        )
        service = cast(SeldonV2ModelService, existing_services[0])
        # even when the deploy decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if not service.is_running:
            service.start(timeout=params.timeout)
        return service

    # invoke the Seldon Core model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    service_config = prepare_service_config(model.uri)
    service = cast(
        SeldonV2ModelService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=params.timeout
        ),
    )

    logger.info(
        f"Seldon deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
