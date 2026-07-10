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
"""Initialization of the Slurm integration.

The Slurm integration provides a step operator that runs individual pipeline
steps as Slurm jobs on an HPC cluster, either over SSH to a login/controller
node or via local ``sbatch`` when the client already runs on the cluster.

Unlike container-based step operators, the Slurm step operator is
container-free: Slurm compute nodes generally cannot run Docker, so steps
execute inside a user-provided Python environment on the cluster (typically on
a shared filesystem), and the pipeline code is shipped to the cluster as an
archive at submission time.
"""

from typing import List, Type

from zenml.integrations.constants import SLURM
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SLURM_STEP_OPERATOR_FLAVOR = "slurm"


class SlurmIntegration(Integration):
    """Definition of the Slurm integration for ZenML."""

    NAME = SLURM
    # paramiko is only needed for the ssh transport; kept in sync with the
    # ssh integration so the two can share the same SSH client.
    REQUIREMENTS = ["paramiko>=3.0.0,<6"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Slurm integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.slurm.flavors import SlurmStepOperatorFlavor

        return [SlurmStepOperatorFlavor]
