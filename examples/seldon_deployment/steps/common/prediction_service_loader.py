#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import cast

from zenml import step
from zenml.integrations.seldon.model_deployers import SeldonModelDeployer
from zenml.integrations.seldon.services import SeldonDeploymentService


@step(enable_cache=False)
def prediction_service_loader(
    pipeline_name: str,
    step_name: str,
    model_name: str,
) -> SeldonDeploymentService:
    """Get the prediction service started by the deployment pipeline."""
    model_deployer = SeldonModelDeployer.get_active_model_deployer()

    services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=model_name,
    )
    if not services:
        raise RuntimeError(
            f"No Seldon Core prediction server deployed by the "
            f"'{step_name}' step in the '{pipeline_name}' "
            f"pipeline for the '{model_name}' model is currently "
            f"running."
        )

    if not services[0].is_running:
        raise RuntimeError(
            f"The Seldon Core prediction server last deployed by the "
            f"'{step_name}' step in the '{pipeline_name}' "
            f"pipeline for the '{model_name}' model is not currently "
            f"running."
        )

    return cast(SeldonDeploymentService, services[0])
