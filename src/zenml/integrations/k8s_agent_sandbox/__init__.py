#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Agent Sandbox integration.

Wraps the ``k8s-agent-sandbox`` Python SDK (the client library for the
``kubernetes-sigs/agent-sandbox`` operator + Google's Agent Substrate
project) as a ZenML ``Sandbox`` stack component.

Works against any Kubernetes cluster running the ``agent-sandbox``
operator. On GKE the operator additionally supports Pod Snapshots;
snapshot / restore support is planned for a follow-up release and is
intentionally absent from this initial skeleton.
"""

from typing import List, Type

from zenml.integrations.constants import K8S_AGENT_SANDBOX
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

K8S_AGENT_SANDBOX_FLAVOR = "k8s_agent_sandbox"


class K8sAgentSandboxIntegration(Integration):
    """Definition of the Agent Sandbox integration for ZenML."""

    NAME = K8S_AGENT_SANDBOX
    REQUIREMENTS = ["k8s-agent-sandbox>=0.1.0", "kubernetes"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declares the stack component flavors for the integration.

        Returns:
            List of new stack component flavors.
        """
        from zenml.integrations.k8s_agent_sandbox.flavors import (
            K8sAgentSandboxFlavor,
        )

        return [K8sAgentSandboxFlavor]
