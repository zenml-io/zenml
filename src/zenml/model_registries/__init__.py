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
"""Initialization of the MLflow Service.

Model registries are centralized repositories that facilitate the collaboration
and management of machine learning models. They provide functionalities such as
version control, metadata tracking, and storage of model artifacts, enabling 
data scientists to efficiently share and keep track of their models within
a team or organization."""

from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    BaseModelRegistryConfig,
    BaseModelRegistryFlavor,
)

__all__ = [
    "BaseModelRegistry",
    "BaseModelRegistryConfig",
    "BaseModelRegistryFlavor",
]
