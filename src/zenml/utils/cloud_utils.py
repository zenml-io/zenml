#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utilities for ZenML Pro."""

from zenml.logger import get_logger
from zenml.models.v2.core.model_version import ModelVersionResponse
from zenml.utils.dashboard_utils import get_model_version_url

logger = get_logger(__name__)


def try_get_model_version_url(model_version: ModelVersionResponse) -> str:
    """Check if a model version is from a ZenML Pro server and return its' URL.

    Args:
        model_version: The model version to check.

    Returns:
        URL if the model version is from a ZenML Pro server, else empty string.
    """
    model_version_url = get_model_version_url(model_version.id)
    if model_version_url:
        return (
            "Dashboard URL for Model "
            f"`{model_version.model.name}::{model_version.name}` "
            "used in this step: \n " + model_version_url
        )
    else:
        return ""
