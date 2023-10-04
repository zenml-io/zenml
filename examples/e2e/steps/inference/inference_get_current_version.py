# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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


from config import MetaConfig
from typing_extensions import Annotated

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def inference_get_current_version() -> Annotated[str, "model_version"]:
    """Get currently tagged model version for deployment.

    Returns:
        The model version of currently tagged model in Registry.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###

    current_version = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        stage=MetaConfig.target_env,
    )[0].version
    logger.info(
        f"Current model version in `{MetaConfig.target_env.value}` is `{current_version}`"
    )

    return current_version
