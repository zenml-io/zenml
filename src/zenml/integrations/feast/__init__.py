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
The Feast integration offers a way to connect to a Feast Feature Store. ZenML
implements a dedicated stack component that you can access as part of your ZenML
steps in the usual ways.
"""

from zenml.integrations.constants import FEAST
from zenml.integrations.integration import Integration


class FeastIntegration(Integration):
    """Definition of Feast integration for ZenML."""

    NAME = FEAST
    REQUIREMENTS = ["feast[redis]>=0.19.4", "redis-server"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.feast import feature_stores  # noqa


FeastIntegration.check_installation()
