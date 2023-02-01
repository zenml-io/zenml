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
"""Enum definitions for Deepchecks integration."""

from zenml.utils.enum_utils import StrEnum


class DeepchecksModuleName(StrEnum):
    """Enum for Deepchecks module names."""

    TABULAR = "tabular"
    VISION = "vision"


class DeepchecksCheckType(StrEnum):
    """Enum for Deepchecks check types."""

    DATA_VALIDATION = "data_validation"
    DATA_DRIFT = "data_drift"
    MODEL_VALIDATION = "model_validation"
    MODEL_DRIFT = "model_drift"
