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
The Seldon Core integration allows you to use the Seldon Core model serving
platform to implement continuous model deployment.
"""
from zenml.integrations.constants import SELDON
from zenml.integrations.integration import Integration


class SeldonIntegration(Integration):
    """Definition of Seldon Core integration for ZenML."""

    NAME = SELDON
    REQUIREMENTS = [
        "kubernetes==18.20.0",
    ]

    @staticmethod
    def activate() -> None:
        """Activate the Seldon Core integration."""
        from zenml.integrations.seldon import model_deployers  # noqa
        from zenml.integrations.seldon import services  # noqa


SeldonIntegration.check_installation()
