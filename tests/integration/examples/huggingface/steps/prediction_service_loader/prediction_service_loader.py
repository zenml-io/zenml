#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from zenml.integrations.huggingface.model_deployers import (
    HuggingFaceModelDeployer,
)
from zenml.integrations.huggingface.services import (
    HuggingFaceDeploymentService,
)


@step(enable_cache=False)
def prediction_service_loader(
    pipeline_name: str,
    model_name: str,
    pipeline_step_name: str,
    running: bool = True,
) -> HuggingFaceDeploymentService:
    """Get the prediction service started by the deployment pipeline.

    Args:
        pipeline_name: name of the pipeline that deployed the MLflow prediction
            server
        step_name: the name of the step that deployed the MLflow prediction
            server
        model_name: the name of the model that is deployed
        running: when this flag is set, the step only returns a running service
    """
    # get the Huggingface model deployer stack component
    model_deployer = HuggingFaceModelDeployer.get_active_model_deployer()

    if services := model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=pipeline_step_name,
        model_name=model_name,
        running=running,
    ):
        return cast(HuggingFaceDeploymentService, services[0])
    else:
        raise RuntimeError(
            f"No Huggingface inference endpoint deployed by step "
            f"'{pipeline_step_name}' in pipeline '{pipeline_name}' with name "
            f"'{model_name}' is currently running."
        )
