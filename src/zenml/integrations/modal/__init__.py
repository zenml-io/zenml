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
"""Modal integration for cloud-native step execution.

The Modal integration sub-module provides a step operator flavor that allows
executing steps on Modal's cloud infrastructure.
"""
from typing import List, Type

from zenml.integrations.constants import MODAL
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

MODAL_STEP_OPERATOR_FLAVOR = "modal"
MODAL_SANDBOX_FLAVOR = "modal"


class ModalIntegration(Integration):
    """Definition of Modal integration for ZenML."""

    NAME = MODAL
    REQUIREMENTS = ["modal>=0.64.49,<1"]

    @classmethod
    def activate(cls) -> None:
        """Activates the Modal integration.

        Imports the Modal materializers module so its
        ``BaseMaterializer`` subclasses register themselves in the
        materializer registry at integration-activation time. Without
        this, ``save_artifact(ModalSandboxSnapshot(...))`` would fall
        back to the generic ``PydanticMaterializer`` by MRO.
        """
        from zenml.integrations.modal import materializers  # noqa: F401

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Modal integration.

        Returns:
            List of new stack component flavors.
        """
        from zenml.integrations.modal.flavors import (
            ModalSandboxFlavor,
            ModalStepOperatorFlavor,
        )

        return [ModalStepOperatorFlavor, ModalSandboxFlavor]


