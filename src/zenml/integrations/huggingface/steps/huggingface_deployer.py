#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the Hugging Face Deployer step."""

from typing import cast

from zenml import get_step_context, step
from zenml.integrations.huggingface.model_deployers.huggingface_model_deployer import (
    HuggingFaceModelDeployer,
)
from zenml.integrations.huggingface.services.huggingface_deployment import (
    HuggingFaceDeploymentService,
    HuggingFaceServiceConfig,
)
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def huggingface_model_deployer_step(
    service_config: HuggingFaceServiceConfig,
    deploy_decision: bool = True,
    timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
) -> HuggingFaceDeploymentService:
    """Hugging Face model deployer pipeline step.

    This step can be used in a pipeline to implement continuous
    deployment with Hugging Face Inference Endpoint.

    Args:
        service_config: Hugging Face deployment service configuration.
        deploy_decision: whether to deploy the model or not
        timeout: the timeout in seconds to wait for the deployment to start

    Returns:
        Huggingface deployment service
    """
    model_deployer = cast(
        HuggingFaceModelDeployer,
        HuggingFaceModelDeployer.get_active_model_deployer(),
    )

    # get pipeline name, step name and run id
    context = get_step_context()
    pipeline_name = context.pipeline.name
    step_name = context.step_run.name

    # update the step configuration with the real pipeline runtime information
    service_config = service_config.copy()
    service_config.pipeline_name = pipeline_name
    service_config.pipeline_step_name = step_name

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        config=service_config.dict()
    )

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{service_config.model_name}'..."
        )
        service = cast(HuggingFaceDeploymentService, existing_services[0])
        # even when the deploy decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if not service.is_running:
            service.start(timeout=timeout)
        return service

    # invoke the Hugging Face model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    service = cast(
        HuggingFaceDeploymentService,
        model_deployer.deploy_model(
            service_config,
            replace=True,
            timeout=timeout,
            service_type=HuggingFaceDeploymentService.SERVICE_TYPE,
        ),
    )

    logger.info(
        f"Hugging Face deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
