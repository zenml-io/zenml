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
from typing import Union, cast

from zenml import step
from zenml.integrations.bentoml.model_deployers.bentoml_model_deployer import (
    BentoMLModelDeployer,
)
from zenml.integrations.bentoml.services.bentoml_container_deployment import BentoMLContainerDeploymentService
from zenml.integrations.bentoml.services.bentoml_local_deployment import (
    BentoMLLocalDeploymentService,
)


@step(enable_cache=False)
def bentoml_prediction_service_loader(
    pipeline_name: str, step_name: str, model_name: str
) -> Union[BentoMLLocalDeploymentService, BentoMLContainerDeploymentService]:
    """Get the BentoML prediction service started by the deployment pipeline.

    Args:
        pipeline_name: name of the pipeline_name that deployed the model.
        step_name: the name of the step that deployed the model.
        model_name: the name of the model that was deployed.
    """
    model_deployer = BentoMLModelDeployer.get_active_model_deployer()

    services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=model_name,
    )
    if not services:
        raise RuntimeError(
            f"No BentoML prediction server deployed by the "
            f"'{step_name}' step in the '{pipeline_name}' "
            f"pipeline for the '{model_name}' model is currently "
            f"running."
        )

    if not services[0].is_running:
        raise RuntimeError(
            f"The BentoML prediction server last deployed by the "
            f"'{step_name}' step in the '{pipeline_name}' "
            f"pipeline for the '{model_name}' model is not currently "
            f"running."
        )
    if services[0].SERVICE_TYPE.name == "bentoml-container-deployment":
        service_instance = cast(BentoMLContainerDeploymentService, services[0])
    else:
        service_instance = cast(BentoMLLocalDeploymentService, services[0])

    return service_instance
