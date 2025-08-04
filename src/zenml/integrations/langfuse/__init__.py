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
"""LangFuse integration for ZenML.

The LangFuse integration allows ZenML to collect and query traces from LangFuse,
an open-source LLM observability platform. This enables monitoring, debugging,
and analysis of LLM applications through ZenML's trace collector interface.
"""

from typing import List, Type

from zenml.integrations.constants import LANGFUSE
from zenml.integrations.integration import Integration


class LangFuseIntegration(Integration):
    """Definition of LangFuse integration for ZenML."""

    NAME = LANGFUSE
    REQUIREMENTS = ["langfuse>=3.2.0"]

    @classmethod
    def flavors(cls) -> List[Type["Flavor"]]:
        """Declare the flavors for the LangFuse integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.langfuse.flavors import (
            LangFuseTraceCollectorFlavor,
        )

        return [
            LangFuseTraceCollectorFlavor,
        ]


LangFuseIntegration.check_installation()