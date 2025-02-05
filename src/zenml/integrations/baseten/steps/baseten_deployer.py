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

from typing import cast

from zenml import get_step_context, step
from zenml.integrations.baseten.model_deployers import BasetenModelDeployer
from zenml.integrations.baseten.services import BasetenDeploymentService
from zenml.logger import get_logger
from zenml.services.service import BaseService

logger = get_logger(__name__)


@step
def baseten_model_deployer_step(
    truss_dir: str,
    model_name: str,
    deploy_decision: bool = True,
    timeout: int = 300,
) -> BaseService:
    """Model deployer pipeline step for Baseten.

    This step deploys a given Truss to Baseten.

    Args:
        truss_dir: The path to the Truss directory.
        model_name: The name of the model.
        deploy_decision: Whether to deploy the model or not.
        timeout: The timeout in seconds.

    Returns:
        The Baseten deployment service.
    """
    # get the current active model deployer
    model_deployer = cast(
        BasetenModelDeployer, BasetenModelDeployer.get_active_model_deployer()
    )

    # get pipeline name, step name and run id
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    step_name = step_context.step_run.name

    # Create a config dict
    config = {
        "model_name": model_name,
        "model_uri": truss_dir,
        "pipeline_name": pipeline_name,
        "run_name": step_context.run_name,
        "pipeline_step_name": step_name,
    }

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=model_name,
    )
    # create a new model deployment and replace an old one if it exists
    if not deploy_decision:
        if existing_services:
            logger.info(
                f"Skipping model deployment because the model quality does not "
                f"meet the criteria. Reusing last model server deployed by step "
                f"'{step_name}' and pipeline '{pipeline_name}' for model "
                f"'{model_name}'..."
            )
            assert isinstance(existing_services[0], BasetenDeploymentService)
            if not existing_services[0].is_running:
                existing_services[0].start(timeout=timeout)
            return existing_services[0]
        else:
            logger.info(
                f"Skipping model deployment because the model quality does not "
                f"meet the criteria and no existing service was found."
            )
            return None

    service = model_deployer.deploy_model(
        replace=True,
        config=config,
        timeout=timeout,
    )

    logger.info(
        f"Baseten deployment service started and reachable at:\n"
        f"   {service.prediction_url}\n"
    )

    return service
