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
"""Implementation of the Deepchecks vision data validator."""

from typing import ClassVar, Type

from deepchecks.vision import Suite as VisionSuite
from deepchecks.vision import VisionData
from deepchecks.vision.suites import full_suite as full_vision_suite

# not part of deepchecks.tabular.checks
from torch.nn import Module
from torch.utils.data.dataloader import DataLoader

from zenml.data_validators import BaseDataValidatorFlavor
from zenml.integrations.deepchecks.data_validators.base_deepchecks_data_validator import (
    BaseDeepchecksDataValidator,
)
from zenml.integrations.deepchecks.enums import DeepchecksModuleName
from zenml.integrations.deepchecks.flavors.deepchecks_vision_data_validator_flavor import (
    DeepchecksVisionDataValidatorFlavor,
)
from zenml.integrations.deepchecks.validation_checks.vision_validation_checks import (
    DeepchecksVisionDataDriftCheck,
    DeepchecksVisionDataValidationCheck,
    DeepchecksVisionModelDriftCheck,
    DeepchecksVisionModelValidationCheck,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class DeepchecksVisionDataValidator(BaseDeepchecksDataValidator):
    """Deepchecks data validator stack component."""

    NAME: ClassVar[str] = "Deepchecks Vision"
    FLAVOR: ClassVar[
        Type[BaseDataValidatorFlavor]
    ] = DeepchecksVisionDataValidatorFlavor

    deepchecks_module = DeepchecksModuleName.VISION
    supported_dataset_types = (DataLoader,)
    supported_model_types = (Module,)
    dataset_class = VisionData
    suite_class = VisionSuite
    full_suite = full_vision_suite()
    data_validation_check_enum = DeepchecksVisionDataValidationCheck
    data_drift_check_enum = DeepchecksVisionDataDriftCheck
    model_validation_check_enum = DeepchecksVisionModelValidationCheck
    model_drift_check_enum = DeepchecksVisionModelDriftCheck
