#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Backward compatibility for the `ExternalArtifact` class."""

from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.logger import get_logger

logger = get_logger(__name__)
logger.warning(
    "The `ExternalArtifact` object was moved to `zenml.artifacts.external_artifact`. "
    "This import path is going to be deprecated. Please consider updating your "
    "code to use `from zenml.artifacts.external_artifact import ExternalArtifact`."
)

__all__ = ["ExternalArtifact"]
