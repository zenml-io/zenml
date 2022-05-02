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
"""
The Great Expectations integration currently enables you to use Great
Expectations as a way of validating your data. It is currently only implemented
to interact with a pre-existing Great Expectations context with expectations
already defined as part of a suite.
"""
from zenml.integrations.constants import GREAT_EXPECTATIONS
from zenml.integrations.integration import Integration


class GreatExpectationsIntegration(Integration):
    """Definition of Great Expectations integration for ZenML."""

    NAME = GREAT_EXPECTATIONS
    REQUIREMENTS = [
        "great-expectations>=0.15.2",
    ]

    @staticmethod
    def activate() -> None:
        """Activate the Great Expectations integration."""
        # from zenml.integrations.great_expectations import data_validators  # noqa


GreatExpectationsIntegration.check_installation()
