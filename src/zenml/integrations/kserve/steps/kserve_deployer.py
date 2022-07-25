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
"""Implementation of the KServe Deployer step."""
from typing import List, Optional, cast

from pydantic import BaseModel, validator

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
from zenml.logger import get_logger
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStepConfig,
    StepEnvironment,
    step,
)
from zenml.steps.step_context import StepContext
from zenml.utils.source_utils import is_inside_repository

logger = get_logger(__name__)

TORCH_HANDLERS = [
    "image_classifier",
    "image_segmenter",
    "object_detector",
    "text_classifier",
]


class TorchServeParameters(BaseModel):
    """KServe PyTorch model deployer step configuration.

    Attributes:
        service_config: KServe deployment service configuration.
        model_class: Path to Python file containing model architecture.
        handler: TorchServe's handler file to handle custom TorchServe inference logic.
        extra_files: Comma separated path to extra dependency files.
        model_version: Model version.
        requirements_file: Path to requirements file.
        torch_config: TorchServe configuration file path.
    """

    model_class: str
    handler: str
    extra_files: Optional[List[str]] = None
    requirements_file: Optional[str] = None
    model_version: Optional[str] = "1.0"
    torch_config: Optional[str] = None

    @validator("model_class")
    def model_class_validate(cls, v: str) -> str:
        """Validate model class file path.

        Args:
            v: model class file path

        Returns:
            model class file path

        Raises:
            ValueError: if model class file path is not valid
        """
        if not v:
            raise ValueError("Model class file path is required.")
        if not is_inside_repository(v):
            raise ValueError(
                "Model class file path must be inside the repository."
            )
        return v

    @validator("handler")
    def handler_validate(cls, v: str) -> str:
        """Validate handler.

        Args:
            v: handler file path

        Returns:
            handler file path

        Raises:
            ValueError: if handler file path is not valid
        """
        if v:
            if v in TORCH_HANDLERS:
                return v
            elif is_inside_repository(v):
                return v
            else:
                raise ValueError(
                    "Handler must be one of the TorchServe handlers",
                    "or a file that exists inside the repository.",
                )
        else:
            raise ValueError("Handler is required.")

    @validator("extra_files")
    def extra_files_validate(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validate extra files.

        Args:
            v: extra files path

        Returns:
            extra files path

        Raises:
            ValueError: if the extra files path is not valid
        """
        extra_files = []
        if v is not None:
            for file_path in v:
                if is_inside_repository(file_path):
                    extra_files.append(file_path)
                else:
                    raise ValueError(
                        "Extra file path must be inside the repository."
                    )
            return extra_files
        return v

    @validator("torch_config")
    def torch_config_validate(cls, v: Optional[str]) -> Optional[str]:
        """Validate torch config file.

        Args:
            v: torch config file path

        Returns:
            torch config file path

        Raises:
            ValueError: if torch config file path is not valid.
        """
        if v:
            if is_inside_repository(v):
                return v
            else:
                raise ValueError(
                    "Torch config file path must be inside the repository."
                )
        return v


class KServeDeployerStepConfig(BaseStepConfig):
    """KServe model deployer step configuration.

    Attributes:
        service_config: KServe deployment service configuration.
        torch_serve_params: TorchServe set of parameters to deploy model.
        timeout: Timeout for model deployment.
    """

    service_config: KServeDeploymentConfig
    torch_serve_parameters: Optional[TorchServeParameters] = None
    timeout: int = DEFAULT_KSERVE_DEPLOYMENT_START_STOP_TIMEOUT


@step(enable_cache=False)
def kserve_model_deployer_step(
    deploy_decision: bool,
    config: KServeDeployerStepConfig,
    context: StepContext,
    model: ModelArtifact,
) -> KServeDeploymentService:
    """KServe model deployer pipeline step.

    This step can be used in a pipeline to implement continuous
    deployment for an ML model with KServe.

    Args:
        deploy_decision: whether to deploy the model or not
        config: configuration for the deployer step
        model: the model artifact to deploy
        context: the step context

    Returns:
        KServe deployment service
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

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=config.service_config.model_name,
    )

    # even when the deploy decision is negative if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing the last model server deployed by step "
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

    # invoke the KServe model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    if config.service_config.predictor == "pytorch":
        # import the prepare function from the step utils
        from zenml.integrations.kserve.steps.kserve_step_utils import (
            prepare_torch_service_config,
        )

        # prepare the service config
        service_config = prepare_torch_service_config(
            model_uri=model.uri,
            output_artifact_uri=context.get_output_artifact_uri(),
            config=config,
        )
    else:
        # import the prepare function from the step utils
        from zenml.integrations.kserve.steps.kserve_step_utils import (
            prepare_service_config,
        )

        # prepare the service config
        service_config = prepare_service_config(
            model_uri=model.uri,
            output_artifact_uri=context.get_output_artifact_uri(),
            config=config,
        )
    service = cast(
        KServeDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=config.timeout
        ),
    )

    logger.info(
        f"KServe deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
        f"    With the hostname: {service.prediction_hostname}."
    )

    return service
