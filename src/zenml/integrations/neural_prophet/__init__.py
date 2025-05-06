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
"""Initialization of the Neural Prophet integration."""

from zenml.integrations.constants import NEURAL_PROPHET
from zenml.integrations.integration import Integration


class NeuralProphetIntegration(Integration):
    """Definition of NeuralProphet integration for ZenML."""

    NAME = NEURAL_PROPHET
    REQUIREMENTS = [
        "neuralprophet>=0.3.2,<0.5.0",
        "holidays>=0.4.1,<0.25.0",
        "tenacity!=8.4.0",  # https://github.com/jd/tenacity/issues/471
    ]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["tenacity"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.neural_prophet import materializers  # noqa

