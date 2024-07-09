#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from typing import Optional

from databricks.sdk.service.serving import (
    ServedModelInputWorkloadSize,
    ServedModelInputWorkloadType,
)
from zenml import logger, step
from zenml.client import Client
from zenml.integrations.databricks.services.databricks_deployment import (
    DatabricksDeploymentConfig,
    DatabricksDeploymentService,
)

logger = logger.get_logger(__name__)


@step
def deploy_to_databricks() -> Optional[DatabricksDeploymentService]:
    # Deploy a model using the Databricks Model Deployer
    zenml_client = Client()
    model_deployer = zenml_client.active_stack.model_deployer
    databricks_deployment_config = DatabricksDeploymentConfig(
        model_name="sklearn-mnist-model",
        model_version="1",
        workload_size=ServedModelInputWorkloadSize.SMALL,
        workload_type=ServedModelInputWorkloadType.CPU,
        scale_to_zero_enabled=True,
        endpoint_secret_name="databricks_token",
    )
    service = model_deployer.deploy_model(
        config=databricks_deployment_config,
        service_type=DatabricksDeploymentService.SERVICE_TYPE,
        timeout=1200,
    )
    logger.info(
        f"The deployed service info: {model_deployer.get_model_server_info(service)}"
    )
    return service
