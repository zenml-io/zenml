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
"""Kubernetes integration for Kubernetes-native orchestration.

The Kubernetes integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubernetes orchestrator with
the CLI tool.
"""
from typing import List, Type

from zenml.integrations.constants import KUBERNETES
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

KUBERNETES_ORCHESTRATOR_FLAVOR = "kubernetes"
KUBERNETES_STEP_OPERATOR_FLAVOR = "kubernetes"


class KubernetesIntegration(Integration):
    """Definition of Kubernetes integration for ZenML."""

    NAME = KUBERNETES
    REQUIREMENTS = ["kubernetes>=21.7,<26"]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = [
        "kfp", # it is used by many others
    ]
    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Kubernetes integration.

        Returns:
            List of new stack component flavors.
        """
        from zenml.integrations.kubernetes.flavors import (
            KubernetesOrchestratorFlavor, KubernetesStepOperatorFlavor
        )

        return [KubernetesOrchestratorFlavor, KubernetesStepOperatorFlavor]


KubernetesIntegration.check_installation()
