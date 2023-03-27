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

from pydantic import BaseModel, validator

from zenml.client import Client
from zenml.constants import MLFLOW_MODEL_FORMAT, MODEL_METADATA_YAML_FILE_NAME
from zenml.environment import Environment
from zenml.exceptions import DoesNotExistException
from zenml.integrations.seldon.constants import (
    SELDON_CUSTOM_DEPLOYMENT,
    SELDON_DOCKER_IMAGE_KEY,
)
from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
    DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT,
    SeldonModelDeployer,
)
from zenml.integrations.seldon.seldon_client import (
    create_seldon_core_custom_spec,
)
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentConfig,
    SeldonDeploymentService,
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
from zenml.utils import io_utils, source_utils
from zenml.utils.materializer_utils import save_model_metadata

logger = get_logger(__name__)


class CustomDeployParameters(BaseModel):
    """Custom model deployer step extra parameters.

    Attributes:
        predict_function: Path to Python file containing predict function.

    Raises:
        ValueError: If predict_function is not specified.
        TypeError: If predict_function is not a callable function.

    Returns:
        predict_function: Path to Python file containing predict function.
    """

    predict_function: str

    @validator("predict_function")
    def predict_function_validate(cls, predict_func_path: str) -> str:
        """Validate predict function.

        Args:
            predict_func_path: predict function path

        Returns:
            predict function path

        Raises:
            ValueError: if predict function path is not valid
            TypeError: if predict function path is not a callable function
        """
        try:
            predict_function = source_utils.load(predict_func_path)
        except AttributeError:
            raise ValueError("Predict function can't be found.")
        if not callable(predict_function):
            raise TypeError("Predict function must be callable.")
        return predict_func_path


class SeldonDeployerStepParameters(BaseParameters):
    """Seldon model deployer step parameters.

    Attributes:
        service_config: Seldon Core deployment service configuration.
        custom_deploy_parameters: custom deployment parameters
        registry_model_name: name of the model in the model registry
        registry_model_version: version of the model in the model registry
        registry_model_stage: stage of the model in the model registry
        replace_existing: whether to replace an existing deployment of the
            model with the same name, this is used only when the model is
            deployed from a model registry stored model.
    """

    service_config: SeldonDeploymentConfig
    custom_deploy_parameters: Optional[CustomDeployParameters] = None
    registry_model_name: Optional[str] = None
    registry_model_version: Optional[str] = None
    registry_model_stage: Optional[ModelVersionStage] = None
    replace_existing: bool = True
    timeout: int = DEFAULT_SELDON_DEPLOYMENT_START_STOP_TIMEOUT


@step(enable_cache=False)
def seldon_model_deployer_step(
    deploy_decision: bool,
    params: SeldonDeployerStepParameters,
    context: StepContext,
    model: UnmaterializedArtifact,
) -> SeldonDeploymentService:
    """Seldon Core model deployer pipeline step.

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
        SeldonModelDeployer, SeldonModelDeployer.get_active_model_deployer()
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

    def prepare_service_config(model_uri: str) -> SeldonDeploymentConfig:
        """Prepare the model files for model serving.

        This creates and returns a Seldon service configuration for the model.

        This function ensures that the model files are in the correct format
        and file structure required by the Seldon Core server implementation
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

        # TODO [ENG-791]: auto-detect built-in Seldon server implementation
        #   from the model artifact type

        # TODO [ENG-792]: validate the model artifact type against the
        #   supported built-in Seldon server implementations
        if params.service_config.implementation == "TENSORFLOW_SERVER":
            # the TensorFlow server expects model artifacts to be
            # stored in numbered subdirectories, each representing a model
            # version
            io_utils.copy_dir(model_uri, os.path.join(served_model_uri, "1"))
        elif params.service_config.implementation == "SKLEARN_SERVER":
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

        service_config = params.service_config.copy()
        service_config.model_uri = served_model_uri
        return service_config

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=params.service_config.model_name,
    )

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{params.service_config.model_name}'..."
        )
        service = cast(SeldonDeploymentService, existing_services[0])
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
        SeldonDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=params.timeout
        ),
    )

    logger.info(
        f"Seldon deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service


@step(enable_cache=False, extra={SELDON_CUSTOM_DEPLOYMENT: True})
def seldon_custom_model_deployer_step(
    deploy_decision: bool,
    params: SeldonDeployerStepParameters,
    context: StepContext,
    model: UnmaterializedArtifact,
) -> SeldonDeploymentService:
    """Seldon Core custom model deployer pipeline step.

    This step can be used in a pipeline to implement the
    the process required to deploy a custom model with Seldon Core.

    Args:
        deploy_decision: whether to deploy the model or not
        params: parameters for the deployer step
        model: the model artifact to deploy
        context: the step context

    Raises:
        ValueError: if the custom deployer is not defined
        DoesNotExistException: if an entity does not exist raise an exception

    Returns:
        Seldon Core deployment service
    """
    # verify that a custom deployer is defined
    if not params.custom_deploy_parameters:
        raise ValueError(
            "Custom deploy parameter is required as part of the step configuration this parameter is",
            "the path of the custom predict function",
        )
    # get the active model deployer
    model_deployer = cast(
        SeldonModelDeployer, SeldonModelDeployer.get_active_model_deployer()
    )

    # get pipeline name, step name, run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    run_name = step_env.run_name
    step_name = step_env.step_name

    # update the step configuration with the real pipeline runtime information
    params.service_config.pipeline_name = pipeline_name
    params.service_config.run_name = run_name
    params.service_config.pipeline_step_name = step_name
    params.service_config.is_custom_deployment = True

    # fetch existing services with the same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=params.service_config.model_name,
    )
    # even when the deploy decision is negative if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not"
            f" meet the criteria. Reusing the last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{params.service_config.model_name}'..."
        )
        service = cast(SeldonDeploymentService, existing_services[0])
        # even when the deployment decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if not service.is_running:
            service.start(timeout=params.timeout)
        return service

    # entrypoint for starting Seldon microservice deployment for custom model
    entrypoint_command = [
        "python",
        "-m",
        "zenml.integrations.seldon.custom_deployer.zenml_custom_model",
        "--model_name",
        params.service_config.model_name,
        "--predict_func",
        params.custom_deploy_parameters.predict_function,
    ]

    # verify if there is an active stack before starting the service
    if not context.stack:
        raise DoesNotExistException(
            "No active stack is available. "
            "Please make sure that you have registered and set a stack."
        )

    image_name = step_env.step_run_info.get_image(key=SELDON_DOCKER_IMAGE_KEY)

    # copy the model files to new specific directory for the deployment
    served_model_uri = os.path.join(
        context.get_output_artifact_uri(), "seldon"
    )
    fileio.makedirs(served_model_uri)
    io_utils.copy_dir(model.uri, served_model_uri)

    # save the model artifact metadata to the YAML file and copy it to the
    # deployment directory
    model_metadata_file = save_model_metadata(model)
    fileio.copy(
        model_metadata_file,
        os.path.join(served_model_uri, MODEL_METADATA_YAML_FILE_NAME),
    )

    # prepare the service configuration for the deployment
    service_config = params.service_config.copy()
    service_config.model_uri = served_model_uri

    # create the specification for the custom deployment
    service_config.spec = create_seldon_core_custom_spec(
        model_uri=service_config.model_uri,
        custom_docker_image=image_name,
        secret_name=model_deployer.kubernetes_secret_name,
        command=entrypoint_command,
    )

    # deploy the service
    service = cast(
        SeldonDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=params.timeout
        ),
    )

    logger.info(
        f"Seldon Core deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service


@step(enable_cache=False)
def seldon_mlflow_registry_deployer_step(
    params: SeldonDeployerStepParameters,
) -> SeldonDeploymentService:
    """Seldon Core model deployer pipeline step.

    This step can be used in a pipeline to implement continuous
    deployment for a MLflow model with Seldon Core.

    Args:
        params: parameters for the deployer step

    Returns:
        Seldon Core deployment service

    Raises:
        ValueError: if registry_model_name is not provided
        ValueError: if neither registry_model_version nor
            registry_model_stage is provided
        ValueError: if the MLflow experiment tracker is not available in the
            active stack
        LookupError: if no model version is found in the MLflow model registry.
    """
    # import here to avoid failing the pipeline if the step is not used

    # check if the MLflow experiment tracker, MLflow model registry and
    # Seldon Core model deployer are available
    if not params.registry_model_name:
        raise ValueError(
            "registry_model_name must be provided to the MLflow"
            "model registry deployer step."
        )
    elif not params.registry_model_version and not params.registry_model_stage:
        raise ValueError(
            "Either registry_model_version or registry_model_stage must"
            "be provided in addition to registry_model_name to the MLflow"
            "model registry deployer step. Since the"
            "mlflow_model_registry_deployer_step is used in conjunction with"
            "the mlflow_model_registry."
        )
    if params.service_config.implementation != "MLFLOW_SERVER":
        raise ValueError(
            "This step only allows MLFLOW_SERVER implementation with seldon"
        )
    # Get the active model deployer
    model_deployer = cast(
        SeldonModelDeployer, SeldonModelDeployer.get_active_model_deployer()
    )

    # fetch the MLflow model registry
    model_registry = Client().active_stack.model_registry
    assert model_registry is not None

    # fetch the model version
    if params.registry_model_version:
        try:
            model_version = model_registry.get_model_version(
                name=params.registry_model_name,
                version=params.registry_model_version,
            )
        except KeyError:
            model_version = None
    elif params.registry_model_stage:
        model_version = model_registry.get_latest_model_version(
            name=params.registry_model_name,
            stage=params.registry_model_stage,
        )
    if not model_version:
        raise LookupError(
            f"No Model Version found for model name "
            f"{params.registry_model_name} and version "
            f"{params.registry_model_version} or stage "
            f"{params.registry_model_stage}"
        )
    if model_version.model_format != MLFLOW_MODEL_FORMAT:
        raise ValueError(
            f"Model version {model_version.version} of model "
            f"{model_version.registered_model.name} is not an MLflow model."
            f"Only MLflow models can be deployed with Seldon Core using "
            f"this step."
        )
    # Prepare the service configuration
    service_config = params.service_config
    service_config.extra_args["registry_model_name"] = (
        model_version.registered_model.name,
    )
    service_config.extra_args["registry_model_version"] = (
        model_version.version,
    )
    service_config.extra_args["registry_model_stage"] = (
        model_version.stage.value,
    )
    service_config.model_uri = model_registry.get_model_uri_artifact_store(
        model_version=model_version,
    )
    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = (
        model_deployer.find_model_server(
            model_name=model_version.registered_model.name,
        )
        if params.replace_existing
        else []
    )
    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if existing_services:
        service = cast(SeldonDeploymentService, existing_services[0])
        # We need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if service.config.model_uri == service_config.model_uri:
            if not service.is_running:
                service.start()
            return service
        else:
            # stop the existing service
            service.stop()

    # invoke the Seldon Core model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    service = cast(
        SeldonDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=params.timeout
        ),
    )

    logger.info(
        f"Seldon deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
