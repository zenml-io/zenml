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
The Deepchecks integration provides a way to validate your data in your pipelines.
It includes a way to detect data anomalies and define checks to ensure quality of
data.

The integration includes custom materializers to store deepchecks `SuiteResults` and
a visualizer to visualize the results in an easy way on a notebook and in your
browser.
"""

from zenml.integrations.constants import DEEPCHECKS
from zenml.integrations.integration import Integration


class DeepchecksIntegration(Integration):
    """Definition of [DeepChecks](https://github.com/deepchecks/deepchecks) integration
    for ZenML."""

    NAME = DEEPCHECKS
    REQUIREMENTS = ["deepchecks>=0.6.3"]

    @staticmethod
    def activate() -> None:
        """Activate the Deepchecks integration."""
        from zenml.integrations.deepchecks import materializers  # noqa
        from zenml.integrations.deepchecks import visualizers  # noqa


DeepchecksIntegration.check_installation()
