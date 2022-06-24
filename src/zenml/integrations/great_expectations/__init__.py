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
"""Great Expectation integration for ZenML.

The Great Expectations integration enables you to use Great Expectations as a
way of profiling and validating your data.
"""

from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import GREAT_EXPECTATIONS
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR = "great_expectations"


class GreatExpectationsIntegration(Integration):
    """Definition of Great Expectations integration for ZenML."""

    NAME = GREAT_EXPECTATIONS
    REQUIREMENTS = [
        "great-expectations~=0.15.11",
    ]

    @staticmethod
    def activate() -> None:
        """Activate the Great Expectations integration."""
        from zenml.integrations.great_expectations import materializers  # noqa

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Great Expectations integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR,
                source="zenml.integrations.great_expectations.data_validators.GreatExpectationsDataValidator",
                type=StackComponentType.DATA_VALIDATOR,
                integration=cls.NAME,
            ),
        ]


GreatExpectationsIntegration.check_installation()
