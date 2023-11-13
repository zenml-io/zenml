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

from typing_extensions import Annotated

from zenml import get_step_context
from zenml.model import ModelConfig
from zenml.models.model_models import ModelVersionResponseModel


def get_model_versions(
    target_env: str,
) -> Tuple[
    Annotated[ModelVersionResponseModel, "latest_version"],
    Annotated[ModelVersionResponseModel, "current_version"],
]:
    """Get latest and currently promoted model versions from Model Control Plane.

    Args:
        target_env: Target stage to search for currently promoted version

    Returns:
        Latest and currently promoted model versions from the Model Control Plane
    """
    latest_version = get_step_context().model_config._get_model_version()
    try:
        current_version = ModelConfig(
            name=latest_version.model.name, version=target_env
        )._get_model_version()
    except KeyError:
        current_version = latest_version

    return latest_version, current_version


def get_model_registry_version(model_version: ModelVersionResponseModel):
    """Get model version in model registry from metadata of a model in the Model Control Plane.

    Args:
        model_version: the Model Control Plane version response
    """
    return (
        model_version.get_model_object("model")
        .metadata["model_registry_version"]
        .value
    )
