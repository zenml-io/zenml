#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Initialization of the Polars integration."""

from zenml.integrations.constants import POLARS
from zenml.integrations.integration import Integration


class PolarsIntegration(Integration):
    """Definition of Polars integration for ZenML."""

    NAME = POLARS
    REQUIREMENTS = [
        "polars>=0.19.5",
        "pyarrow>=12.0.0"
    ]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["pyarrow"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.polars import materializers  # noqa

