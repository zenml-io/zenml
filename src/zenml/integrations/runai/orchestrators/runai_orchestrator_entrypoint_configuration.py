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
"""Entrypoint configuration for the Run:AI orchestrator workload."""

from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from uuid import UUID

SNAPSHOT_ID_OPTION = "snapshot_id"
RUN_ID_OPTION = "run_id"


class RunAIOrchestratorEntrypointConfiguration:
    """Entrypoint configuration for Run:AI orchestrator workload."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running this entrypoint.

        Returns:
            Entrypoint options.
        """
        return {SNAPSHOT_ID_OPTION}

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        Returns:
            Entrypoint command.
        """
        return [
            "python",
            "-m",
            "zenml.integrations.runai.orchestrators.runai_orchestrator_entrypoint",
        ]

    @classmethod
    def get_entrypoint_arguments(
        cls,
        snapshot_id: "UUID",
        run_id: Optional["UUID"] = None,
    ) -> List[str]:
        """Gets all arguments the entrypoint command should be called with.

        Args:
            snapshot_id: ID of the pipeline snapshot.
            run_id: Optional ID of the pipeline run.

        Returns:
            List of entrypoint arguments.
        """
        args = [
            f"--{SNAPSHOT_ID_OPTION}",
            str(snapshot_id),
        ]

        if run_id:
            args.append(f"--{RUN_ID_OPTION}")
            args.append(str(run_id))

        return args
