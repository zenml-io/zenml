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
"""Initialization of the Huggingface integration."""
from typing import List, Type

from zenml.integrations.constants import HUGGINGFACE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

HUGGINGFACE_MODEL_DEPLOYER_FLAVOR = "huggingface"
HUGGINGFACE_SERVICE_ARTIFACT = "hf_deployment_service"


class HuggingfaceIntegration(Integration):
    """Definition of Huggingface integration for ZenML."""

    NAME = HUGGINGFACE
    REQUIREMENTS = [
        "transformers<=4.31",
        "datasets",
        "huggingface_hub>0.19.0",
        "accelerate",
        "bitsandbytes>=0.41.3",
        "peft",
        # temporary fix for CI issue similar to:
        # - https://github.com/huggingface/datasets/issues/6737
        # - https://github.com/huggingface/datasets/issues/6697
        # TODO try relaxing it back going forward
        "fsspec<=2023.12.0",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.huggingface import materializers  # noqa
        from zenml.integrations.huggingface import services

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Huggingface integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.huggingface.flavors import (
            HuggingFaceModelDeployerFlavor,
        )

        return [HuggingFaceModelDeployerFlavor]


HuggingfaceIntegration.check_installation()
