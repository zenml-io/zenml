# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from typing import Optional

from databricks.sdk.service.serving import (
    ServedModelInputWorkloadSize,
    ServedModelInputWorkloadType,
)
from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.integrations.databricks.services.databricks_deployment import (
    DatabricksDeploymentConfig,
    DatabricksDeploymentService,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def deployment_deploy() -> (
    Annotated[
        Optional[DatabricksDeploymentService],
        ArtifactConfig(name="databricks_deployment", is_deployment_artifact=True),
    ]
):
    """Predictions step.

    This is an example of a predictions step that takes the data in and returns
    predicted values.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        dataset_inf: The inference dataset.

    Returns:
        The predictions as pandas series
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    model = get_step_context().model

    # deploy predictor service
    zenml_client = Client()
    model_deployer = zenml_client.active_stack.model_deployer
    databricks_deployment_config = DatabricksDeploymentConfig(
        model_name=model.name,
        model_version=model.run_metadata["model_registry_version"].value,
        workload_size=ServedModelInputWorkloadSize.SMALL,
        workload_type=ServedModelInputWorkloadType.CPU,
        scale_to_zero_enabled=True,
        endpoint_secret_name="databricks_token",
    )
    deployment_service = model_deployer.deploy_model(
        config=databricks_deployment_config,
        service_type=DatabricksDeploymentService.SERVICE_TYPE,
        timeout=1200,
    )
    logger.info(
        f"The deployed service info: {model_deployer.get_model_server_info(deployment_service)}"
    )
    return deployment_service
