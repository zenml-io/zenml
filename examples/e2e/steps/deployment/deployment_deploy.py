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

from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.services.service import BaseDeploymentService

mlflow_enabled = False
try:
    from zenml.integrations.mlflow.steps.mlflow_deployer import (
        mlflow_model_registry_deployer_step,
    )

    mlflow_enabled = True
except ImportError:
    pass


logger = get_logger(__name__)


@step
def deployment_deploy() -> (
    Annotated[
        Optional[BaseDeploymentService],
        ArtifactConfig(name="mlflow_deployment", is_deployment_artifact=True),
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
    model_deployer = Client().active_stack.model_deployer
    current_model = get_step_context().model

    if mlflow_enabled:
        if Client().active_stack.orchestrator.flavor == "local":
            logger.warning(
                "Skipping deployment as the orchestrator is not local."
            )
            deployment_service = None
        else:
            # deploy predictor service
            deployment_service = (
                mlflow_model_registry_deployer_step.entrypoint(
                    registry_model_name=current_model.name,
                    registry_model_version=current_model.run_metadata[
                        "model_registry_version"
                    ],
                    replace_existing=True,
                )
            )
    elif model_deployer is not None:
        from zenml.integrations.gcp.model_deployers import (
            VertexModelDeployer,
        )
        from zenml.integrations.gcp.services.vertex_deployment import (
            VertexDeploymentConfig,
            VertexDeploymentService,
        )

        if isinstance(model_deployer, VertexModelDeployer):

            vertex_deployment_config = VertexDeploymentConfig(
                location=model_deployer.config.location,
                name="zenml-vertex-e2e",
                model_name=current_model.name,
                model_version=current_model.version,
                model_id=f"{current_model.name}_{current_model.version}",
            )
            deployment_service = model_deployer.deploy_model(
                config=vertex_deployment_config,
                service_type=VertexDeploymentService.SERVICE_TYPE,
            )

            logger.info(
                f"The deployed service info: {model_deployer.get_model_server_info(deployment_service)}"
            )
    else:
        logger.warning(
            "Skipping deployment as no model deployer is available."
        )
        deployment_service = None

    ### YOUR CODE ENDS HERE ###
    return deployment_service
