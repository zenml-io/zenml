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
"""Implementation of the Deepchecks tabular data validator."""

from typing import (
    ClassVar,
    Type,
)

import pandas as pd
from deepchecks.tabular import Dataset as TabularData
from deepchecks.tabular import Suite as TabularSuite
from deepchecks.tabular.suites import full_suite as full_tabular_suite
from sklearn.base import ClassifierMixin

from zenml.data_validators import BaseDataValidatorFlavor
from zenml.integrations.deepchecks.data_validators.base_deepchecks_data_validator import (
    BaseDeepchecksDataValidator,
)
from zenml.integrations.deepchecks.enums import DeepchecksModuleName
from zenml.integrations.deepchecks.flavors.deepchecks_tabular_data_validator_flavor import (
    DeepchecksTabularDataValidatorFlavor,
)
from zenml.integrations.deepchecks.validation_checks.tabular_validation_checks import (
    DeepchecksTabularDataDriftCheck,
    DeepchecksTabularDataValidationCheck,
    DeepchecksTabularModelDriftCheck,
    DeepchecksTabularModelValidationCheck,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class DeepchecksTabularDataValidator(BaseDeepchecksDataValidator):
    """Deepchecks data validator stack component."""

    NAME: ClassVar[str] = "Deepchecks Tabular"
    FLAVOR: ClassVar[
        Type[BaseDataValidatorFlavor]
    ] = DeepchecksTabularDataValidatorFlavor

    deepchecks_module = DeepchecksModuleName.TABULAR
    supported_dataset_types = (pd.DataFrame,)
    supported_model_types = (ClassifierMixin,)
    dataset_class = TabularData
    suite_class = TabularSuite
    full_suite = full_tabular_suite()
    data_validation_check_enum = DeepchecksTabularDataValidationCheck
    data_drift_check_enum = DeepchecksTabularDataDriftCheck
    model_validation_check_enum = DeepchecksTabularModelValidationCheck
    model_drift_check_enum = DeepchecksTabularModelDriftCheck
