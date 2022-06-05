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
import tempfile
from typing import Optional, cast

from model_archiver.model_packaging import package_model
from model_archiver.model_packaging_utils import ModelExportUtils
from pydantic import BaseModel

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.environment import Environment
from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (
    DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT,
    KServeModelDeployer,
)
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
    KServeDeploymentService,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStepConfig,
    StepEnvironment,
    step,
)
from zenml.steps.step_context import StepContext
from zenml.utils.source_utils import get_source_root_path

logger = get_logger(__name__)


class KServePytorchDeployerStepConfig(BaseStepConfig):
    """KServe pytorch model deployer step configuration

    Attributes:

        service_config: KServe deployment service configuration.

        model_file:     Path to python file containing model architecture.
                        This parameter is mandatory for eager mode models.
                        The model architecture file must contain only one
                        class definition extended from torch.nn.modules.

        handler:        TorchServe's default handler name  or handler python
                        file path to handle custom TorchServe inference logic.

        extra_files:    Comma separated path to extra dependency files.
    """

    service_config: KServeDeploymentConfig
    model_class_file: Optional[str] = None
    handler: Optional[str] = None
    extra_files: Optional[str] = None
    requirements_file: Optional[str] = None
    model_version: Optional[int] = None
    torch_config: Optional[str] = "config.properties"
    timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT


class TorchModelArchiver(BaseModel):
    """The Kubernetes status condition entry for a Seldon Deployment.

    Attributes:

        type: Type of runtime condition.
        status: Status of the condition.
        reason: Brief CamelCase string containing reason for the condition's
            last transition.
        message: Human-readable message indicating details about last
            transition.
    """

    model_name: str
    serialized_file: str
    model_file: str
    handler: str
    export_path: str
    extra_files: Optional[str] = None
    model_version: Optional[int] = None
    requirements_file: Optional[str] = None
    runtime: Optional[str] = "python3"
    version: Optional[int] = None
    force: Optional[bool] = None
    archive_format: Optional[str] = "default"


@step(enable_cache=False)
def kserve_pytorch_model_deployer_step(
    deploy_decision: bool,
    config: KServePytorchDeployerStepConfig,
    context: StepContext,
    model: ModelArtifact,
) -> KServeDeploymentService:
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
    model_deployer = KServeModelDeployer.get_active_model_deployer()

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    pipeline_run_id = step_env.pipeline_run_id
    step_name = step_env.step_name

    # update the step configuration with the real pipeline runtime information
    config.service_config.pipeline_name = pipeline_name
    config.service_config.pipeline_run_id = pipeline_run_id
    config.service_config.pipeline_step_name = step_name

    def prepare_service_config(model_uri: str) -> KServeDeploymentConfig:
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
        deployment_folder_uri = os.path.join(
            context.get_output_artifact_uri(), "kserve"
        )
        served_model_uri = os.path.join(deployment_folder_uri, "model-store")
        config_propreties_uri = os.path.join(deployment_folder_uri, "config")
        fileio.makedirs(served_model_uri)
        fileio.makedirs(config_propreties_uri)

        # TODO [ENG-773]: determine how to formalize how models are organized into
        #   folders and sub-folders depending on the model type/format and the
        #   Seldon Core protocol used to serve the model.

        # TODO [ENG-791]: auto-detect built-in kserve server implementation
        #   from the model artifact type

        # TODO [ENG-792]: validate the model artifact type against the
        #   supported built-in Seldon server implementations
        if config.service_config.predictor == "pytorch":

            # Create a temporary folder
            temp_dir = tempfile.mkdtemp(prefix="zenml-pytorch-temp-")
            tmp_model_uri = os.path.join(str(temp_dir), "chekpoint.pt")

            # Copy from artifact store to temporary file
            fileio.copy(model_uri, tmp_model_uri)

            torch_archiver_args = TorchModelArchiver(
                model_name=config.service_config.model_name,
                serialized_file=tmp_model_uri,
                model_file=os.path.join(
                    get_source_root_path(), config.model_class_file
                ),
                handler=os.path.join(get_source_root_path(), config.handler),
                export_path=temp_dir,
            )

            manifest = ModelExportUtils.generate_manifest_json(
                torch_archiver_args
            )
            package_model(torch_archiver_args, manifest=manifest)

            # Copy from temporary file to artifact store
            archived_model_uri = os.path.join(
                temp_dir, f"{config.service_config.model_name}.mar"
            )
            if not fileio.exists(archived_model_uri):
                raise RuntimeError(
                    f"Expected torch archived model artifact was not found at "
                    f"{archived_model_uri}"
                )

            # Copy the torch model archive artifact to the model store
            fileio.copy(
                archived_model_uri,
                os.path.join(
                    served_model_uri, f"{config.service_config.model_name}.mar"
                ),
            )
            # Copy the torch model config to the model store
            fileio.copy(
                os.path.join(get_source_root_path(), config.torch_config),
                os.path.join(config_propreties_uri, "config.properties"),
            )

        service_config = config.service_config.copy()
        service_config.model_uri = deployment_folder_uri
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
        service = cast(KServeDeploymentService, existing_services[0])
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
        KServeDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=config.timeout
        ),
    )

    logger.info(
        f"Seldon deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
