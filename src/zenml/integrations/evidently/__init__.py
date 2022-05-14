#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
The Evidently integration provides a way to monitor your models in production.
It includes a way to detect data drift and different kinds of model performance
issues.

The results of Evidently calculations can either be exported as an interactive
dashboard (visualized as an html file or in your Jupyter notebook), or as a JSON
file.
"""

from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import EVIDENTLY, WANDB
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

EVIDENTLY_DRIFT_DETECTOR_FLAVOR = "evidently"


class EvidentlyIntegration(Integration):
    """Definition of [Evidently](https://github.com/evidentlyai/evidently) integration
    for ZenML."""

    NAME = EVIDENTLY
    REQUIREMENTS = ["evidently==v0.1.41.dev0"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the MLflow integration"""
        return [
            FlavorWrapper(
                name=EVIDENTLY_DRIFT_DETECTOR_FLAVOR,
                source="zenml.integrations.evidently.drift_detectors.evidently_drift_detector.EvidentlyDriftDetector",
                type=StackComponentType.DRIFT_DETECTOR,
                integration=cls.NAME,
            )
        ]


EvidentlyIntegration.check_installation()
