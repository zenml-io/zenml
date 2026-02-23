#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""SSH integration for remote step execution via SSH and Docker.

The SSH integration provides a step operator that connects to a remote Linux
host over SSH and runs ZenML step entrypoints inside Docker containers, with
optional GPU selection and per-GPU mutual exclusion via flock.
"""

from typing import List, Type

from zenml.integrations.constants import SSH
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SSH_STEP_OPERATOR_FLAVOR = "ssh"


class SSHIntegration(Integration):
    """Definition of SSH integration for ZenML."""

    NAME = SSH
    REQUIREMENTS = ["paramiko>=3.0.0,<5"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the SSH integration.

        Returns:
            List of new stack component flavors.
        """
        from zenml.integrations.ssh.flavors import SSHStepOperatorFlavor

        return [SSHStepOperatorFlavor]
