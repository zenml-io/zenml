#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Evidently data validator flavor."""

from typing import TYPE_CHECKING, Type

from zenml.data_validators.base_data_validator import BaseDataValidatorFlavor
from zenml.integrations.evidently import EVIDENTLY_DATA_VALIDATOR_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.evidently.data_validators import (
        EvidentlyDataValidator,
    )


class EvidentlyDataValidatorFlavor(BaseDataValidatorFlavor):
    """Evidently data validator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return EVIDENTLY_DATA_VALIDATOR_FLAVOR

    @property
    def implementation_class(self) -> Type["EvidentlyDataValidator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.evidently.data_validators import (
            EvidentlyDataValidator,
        )

        return EvidentlyDataValidator
