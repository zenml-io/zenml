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
"""Entrypoint configuration for the Lightning master/orchestrator VM."""

from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from uuid import UUID

RUN_NAME_OPTION = "run_name"
SNAPSHOT_ID_OPTION = "snapshot_id"


class LightningOrchestratorEntrypointConfiguration:
    """Entrypoint configuration for the Lightning master/orchestrator VM."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all the options required for running this entrypoint.

        Returns:
            Entrypoint options.
        """
        options = {
            RUN_NAME_OPTION,
            SNAPSHOT_ID_OPTION,
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
            "zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint",
        ]
        return command

    @classmethod
    def get_entrypoint_arguments(
        cls,
        run_name: str,
        snapshot_id: "UUID",
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            run_name: Name of the ZenML run.
            snapshot_id: ID of the snapshot.

        Returns:
            List of entrypoint arguments.
        """
        args = [
            f"--{RUN_NAME_OPTION}",
            run_name,
            f"--{SNAPSHOT_ID_OPTION}",
            str(snapshot_id),
        ]

        return args
