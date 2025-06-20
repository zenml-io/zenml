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
"""Entrypoint configuration for the Kubernetes master/orchestrator pod."""

from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from uuid import UUID

DEPLOYMENT_ID_OPTION = "deployment_id"
RUN_ID_OPTION = "run_id"


class KubernetesOrchestratorEntrypointConfiguration:
    """Entrypoint configuration for the k8s master/orchestrator pod."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options required for running this entrypoint.

        Returns:
            Entrypoint options.
        """
        options = {
            DEPLOYMENT_ID_OPTION,
        }
        return options

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        Returns:
            Entrypoint command.
        """
        command = [
            "python",
            "-m",
            "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint",
        ]
        return command

    @classmethod
    def get_entrypoint_arguments(
        cls,
        deployment_id: "UUID",
        run_id: Optional["UUID"] = None,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            deployment_id: ID of the deployment.
            run_id: Optional ID of the pipeline run. Not set for scheduled runs.

        Returns:
            List of entrypoint arguments.
        """
        args = [
            f"--{DEPLOYMENT_ID_OPTION}",
            str(deployment_id),
        ]

        if run_id:
            args.append(f"--{RUN_ID_OPTION}")
            args.append(str(run_id))

        return args
