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


from typing import Tuple

from config import MetaConfig
from typing_extensions import Annotated

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def promote_get_versions() -> (
    Tuple[Annotated[str, "latest_version"], Annotated[str, "current_version"]]
):
    """Step to get latest and currently tagged model version from Model Registry.

    This is an example of a model version extraction step. It will retrieve 2 model
    versions from Model Registry: latest and currently promoted to target
    environment (Production, Staging, etc).

    Returns:
        The model versions: latest and current. If not current version - returns same
            for both.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    none_versions = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        stage=None,
    )
    latest_versions = none_versions[0].version
    logger.info(f"Latest model version is {latest_versions}")

    target_versions = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        stage=MetaConfig.target_env,
    )
    current_version = latest_versions
    if target_versions:
        current_version = target_versions[0].version
        logger.info(f"Currently promoted model version is {current_version}")
    else:
        logger.info("No currently promoted model version found.")
    ### YOUR CODE ENDS HERE ###

    return latest_versions, current_version
