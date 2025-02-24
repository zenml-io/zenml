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

import os
import time
from typing import Any, Dict, Optional, cast

from zenml import get_step_context, step
from zenml.integrations.baseten.model_deployers import BasetenModelDeployer
from zenml.integrations.baseten.services import (
    BasetenDeploymentConfig,
)
from zenml.logger import get_logger
from zenml.services import BaseService
from zenml.utils.io_utils import isdir

logger = get_logger(__name__)


@step
def baseten_model_deployer_step(
    truss_dir: str,
    model_name: str,
    framework: str = "sklearn",
    deploy_decision: bool = True,
    timeout: int = 300,
    replace: bool = True,
    service_name: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None,
    resources: Optional[Dict[str, Any]] = None,
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
        service_name: Optional custom name for the service.
        environment_variables: Optional environment variables for the deployment.
        resources: Optional resource requirements (cpu, memory, use_gpu).

    Returns:
        The Baseten deployment service.

    Raises:
        ValueError: If the truss_dir does not exist or other validation fails.
        RuntimeError: If deployment fails.
    """
    # Validate deploy_decision
    if not deploy_decision:
        logger.info("Skipping deployment due to deploy_decision=False")
        return None

    # Validate truss_dir exists
    if not truss_dir:
        raise ValueError("truss_dir parameter is required")

    # Convert to absolute path if relative
    if not os.path.isabs(truss_dir):
        truss_dir = os.path.abspath(truss_dir)

    if not os.path.exists(truss_dir):
        raise ValueError(f"Truss directory not found: {truss_dir}")

    if not isdir(truss_dir):
        raise ValueError(f"truss_dir must be a directory: {truss_dir}")

    # Verify config.yaml exists in the Truss directory
    config_path = os.path.join(truss_dir, "config.yaml")
    if not os.path.exists(config_path):
        raise ValueError(
            f"config.yaml not found in Truss directory: {config_path}"
        )

    # Verify model directory exists
    model_dir = os.path.join(truss_dir, "model")
    if not os.path.exists(model_dir):
        raise ValueError(
            f"model directory not found in Truss directory: {model_dir}"
        )

    # Verify model.py exists
    model_py_path = os.path.join(model_dir, "model.py")
    if not os.path.exists(model_py_path):
        raise ValueError(
            f"model.py not found in Truss model directory: {model_py_path}"
        )

    # Get the current active model deployer
    model_deployer = cast(
        BasetenModelDeployer, BasetenModelDeployer.get_active_model_deployer()
    )

    # Get pipeline name, step name and run id
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    step_name = step_context.step_run.name

    # Use run_id as run_name
    try:
        run_id = str(step_context.pipeline_run.id)
    except (AttributeError, TypeError):
        # Fall back to timestamp if pipeline_run.id is not available
        run_id = str(int(time.time()))

    # Use service_name from parameter or generate one
    if not service_name:
        service_name = f"{model_name}-{run_id}"

    # If replace=False, check for existing deployments
    if not replace:
        existing_services = model_deployer.find_model_server(
            pipeline_name=pipeline_name,
            pipeline_step_name=step_name,
            model_name=model_name,
            service_name=service_name,
        )
        if existing_services:
            logger.info(
                f"Found existing deployment for model '{model_name}' and "
                f"service name '{service_name}'. Skipping deployment."
            )

            # Check if service is running
            service = existing_services[0]
            if not service.is_running:
                logger.info(
                    "Existing service is not running. Starting service..."
                )
                try:
                    service.start(timeout=timeout)
                except Exception as e:
                    logger.warning(f"Failed to start existing service: {e}")

            return service

    # Create deployment config with enhanced parameters
    config = BasetenDeploymentConfig(
        name=model_name,
        uri=truss_dir,
        framework=framework,
        pipeline_name=pipeline_name,
        run_name=run_id,
        pipeline_step_name=step_name,
        service_name=service_name,
    )

    # Deploy the model with detailed logging
    logger.info(f"Deploying model '{model_name}' to Baseten...")
    logger.info(f"Truss directory: {truss_dir}")
    logger.info(f"Service name: {service_name}")
    logger.info(f"Timeout: {timeout} seconds")
    logger.info(f"Replace existing: {replace}")

    try:
        service = model_deployer.deploy_model(
            config=config,
            replace=replace,
            timeout=timeout,
        )

        logger.info(
            f"Model '{model_name}' successfully deployed to Baseten. "
            f"Service ID: {service.id}"
        )

        # Log the prediction URL
        if service.prediction_url:
            logger.info(f"Prediction URL: {service.prediction_url}")

        return service

    except Exception as e:
        logger.error(f"Failed to deploy model to Baseten: {str(e)}")
        raise RuntimeError(f"Failed to deploy model to Baseten: {str(e)}")
