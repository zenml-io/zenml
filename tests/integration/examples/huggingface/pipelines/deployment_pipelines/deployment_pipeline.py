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

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import HUGGINGFACE
from zenml.integrations.huggingface.services import HuggingFaceServiceConfig
from zenml.integrations.huggingface.steps import (
    huggingface_model_deployer_step,
)

docker_settings = DockerSettings(
    required_integrations=[HUGGINGFACE],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def huggingface_deployment_pipeline(
    model_name: str = "hf",
    timeout: int = 1200,
):
    service_config = HuggingFaceServiceConfig(model_name=model_name)

    # Deployment step
    huggingface_model_deployer_step(
        service_config=service_config,
        timeout=timeout,
    )
