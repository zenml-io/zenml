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
"""Implementation of the Baseten model deployer pipeline step."""

from typing import cast, Optional

from zenml import get_step_context, step
from zenml.integrations.baseten.model_deployers import BasetenModelDeployer
from zenml.integrations.baseten.services import (
    BasetenDeploymentConfig,
    BasetenDeploymentService,
)
from zenml.logger import get_logger
from zenml.services import BaseService

logger = get_logger(__name__)


@step
def baseten_model_deployer_step(
    truss_dir: str,
    model_name: str,
    framework: str = "sklearn",
    deploy_decision: bool = True,
    timeout: int = 300,
    replace: bool = True,
) -> BaseService:
    """Model deployer pipeline step for Baseten.

    This step deploys a given Truss to Baseten.

    Args:
        truss_dir: The path to the Truss directory.
        model_name: The name of the model.
        framework: The framework/type of the model (e.g., sklearn).
        deploy_decision: Whether to deploy the model or not.
        timeout: The timeout in seconds.
        replace: Whether to replace an existing deployment.

    Returns:
        The Baseten deployment service.
    """
    if not deploy_decision:
        logger.info("Skipping deployment due to deploy_decision=False")
        return None

    # Get the current active model deployer
    model_deployer = cast(
        BasetenModelDeployer, BasetenModelDeployer.get_active_model_deployer()
    )

    # Get pipeline name, step name and run id
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    step_name = step_context.step_run.name

    # If replace=False, check for existing deployments
    if not replace:
        existing_services = model_deployer.find_model_server(
            pipeline_name=pipeline_name,
            pipeline_step_name=step_name,
            model_name=model_name,
        )
        if existing_services:
            logger.info(
                f"Found existing deployment for model '{model_name}' and "
                f"pipeline step '{step_name}'. Skipping deployment."
            )
            return existing_services[0]

    # Create deployment config
    config = BasetenDeploymentConfig(
        name=model_name,
        uri=truss_dir,
        framework=framework,
        pipeline_name=pipeline_name,
        run_name=step_context.run_name,
        pipeline_step_name=step_name,
    )

    # Deploy the model
    logger.info(f"Deploying model '{model_name}' to Baseten...")
    service = model_deployer.deploy_model(
        config=config,
        timeout=timeout,
    )

    logger.info(
        f"Model '{model_name}' successfully deployed to Baseten. "
        f"Service ID: {service.id}"
    )
    return service
