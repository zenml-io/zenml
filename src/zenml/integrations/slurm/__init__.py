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

The Slurm integration runs ZenML pipelines on an HPC cluster managed by the
Slurm scheduler. It provides two stack components:

- a step operator that runs a single step as a Slurm job (delegating the rest
  of the pipeline to another orchestrator), and
- an orchestrator that submits the whole pipeline as a graph of Slurm jobs
  wired together with ``sbatch`` dependencies.

Both run the step's standard ZenML Docker image on the compute node with a
rootless HPC container runtime (Apptainer/Singularity by default, or NVIDIA
Pyxis, or the Docker daemon where available), so code delivery uses ZenML's
standard image build. Submission goes over SSH to a login/controller node, or
via local ``sbatch`` when the client already runs on the cluster.
"""

from typing import List, Type

from zenml.integrations.constants import SLURM
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

SLURM_STEP_OPERATOR_FLAVOR = "slurm"
SLURM_ORCHESTRATOR_FLAVOR = "slurm"


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
        from zenml.integrations.slurm.flavors import (
            SlurmOrchestratorFlavor,
            SlurmStepOperatorFlavor,
        )

        return [SlurmStepOperatorFlavor, SlurmOrchestratorFlavor]
