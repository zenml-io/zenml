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
"""Initialization of the PyCaret integration."""

from zenml.integrations.constants import PYCARET
from zenml.integrations.integration import Integration


class PyCaretIntegration(Integration):
    """Definition of PyCaret integration for ZenML."""

    NAME = PYCARET
    REQUIREMENTS = [
        "pycaret>=3.0.0",
        "scikit-learn",
        "xgboost",
        "catboost",
        "lightgbm",
    ]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = [
        "scikit-learn",
        "xgboost",
        "catboost",
        "lightgbm",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.pycaret import materializers  # noqa

