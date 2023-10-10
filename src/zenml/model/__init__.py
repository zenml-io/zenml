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

"""Initialization of ZenML model.
ZenML model support Model Control Plane feature.
"""

from zenml.model.model_config import ModelConfig
from zenml.model.artifact_config import (
    ArtifactConfig,
    ModelArtifactConfig,
    DeploymentArtifactConfig,
)
from zenml.model.link_output_to_model import link_output_to_model


__all__ = [
    "ArtifactConfig",
    "DeploymentArtifactConfig",
    "ModelArtifactConfig",
    "ModelConfig",
    "link_output_to_model",
]
