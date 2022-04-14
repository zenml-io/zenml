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
import os
from pathlib import Path
from typing import Any, Optional

import wandb

from zenml.environment import BaseEnvironmentComponent
from zenml.logger import get_logger

logger = get_logger(__name__)

WANDB_ENVIRONMENT_NAME = "wandb"
WANDB_STEP_ENVIRONMENT_NAME = "wandb_step"


class WandbEnvironment(BaseEnvironmentComponent):
    """Manages the global wandb environment in the form of an Environment
    component. To access it inside your step function or in the post-execution
    workflow:

    ```python
    from zenml.environment import Environment
    from zenml.integrations.wandb.wandb_environment import WANDB_ENVIRONMENT_NAME


    @step
    def my_step(...)
        env = Environment[WANDB_ENVIRONMENT_NAME]
        do_something_with(env.wandb_tracking_uri)
    ```

    """

    NAME = WANDB_ENVIRONMENT_NAME

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize a wandb environment component.

        Args:
            root: Optional root directory of the ZenML repository. If no path
                is given, the default repository location will be used.
        """
        super().__init__()
        # TODO [ENG-316]: Implement a way to get the wandb token and set
        #  it as env variable at WANDB_TRACKING_TOKEN
        self._wandb_api_key = os.getenv("WANDB_API_KEY")

    def activate(self) -> None:
        """Activate the wandb environment for the current stack."""
        return super().activate()

    def deactivate(self) -> None:
        logger.debug("Resetting the wandb tracking uri to local")
        return super().deactivate()

    @property
    def api_key(self) -> Optional[str]:
        """Returns the wandb tracking URI for the current stack."""
        return self._wandb_api_key


class WandbStepEnvironment(BaseEnvironmentComponent):
    """Provides information about a wandb step environment.
    To access it inside your step function:

    ```python
    from zenml.environment import Environment
    from zenml.integrations.wandb.wandb_environment import WANDB_STEP_ENVIRONMENT_NAME


    @step
    def my_step(...)
        env = Environment[WANDB_STEP_ENVIRONMENT_NAME]
        do_something_with(env.wandb_tracking_uri)
    ```

    """

    NAME = WANDB_STEP_ENVIRONMENT_NAME

    def __init__(
        self,
        project_name: str,
        experiment_name: str,
        run_name: str,
        entity: Optional[str] = None,
    ):
        """Initialize a wandb step environment component.

        Args:
            experiment_name: the experiment name under which all wandb
                artifacts logged under the current step will be tracked.
                If no wandb experiment with this name exists, one will
                be created when the environment component is activated.
            run_name: the name of the wandb run associated with the current
                step. If a run with this name does not exist, one will be
                created when the environment component is activated,
                otherwise the existing run will be reused.
        """
        super().__init__()
        self._experiment_name = experiment_name
        self._project_name = project_name
        self._experiment = None
        self._run_name = run_name
        self._entity = entity
        self._run = None

    def _create_or_reuse_wandb_run(self) -> None:
        """Create or reuse a wandb run for the current step.

        IMPORTANT: This function might cause a race condition. If two or more
        processes call it at the same time and with the same arguments, it could
        lead to a situation where two or more wandb runs with the same name
        and different IDs are created.
        """
        # Set which experiment is used within wandb
        logger.debug("Setting the wandb project name to %s", self._project_name)
        logger.debug(
            "Setting the wandb group name to %s", self._experiment_name
        )
        api = wandb.Api()
        run_exists = False
        entity = (
            os.getenv("WANDB_ENTITY") if self._entity is None else self._entity
        )
        runs = api.runs(f"{entity}/{self._project_name}")
        for run in runs:
            if run.name == self._run_name:
                run_exists = True
                # Re-use old run
                self._run = run
        if not run_exists:
            # Create a new run
            wandb.finish()
            self._run = wandb.init(
                project=self._project_name, name=self._run_name, entity=entity
            )

    def activate(self) -> None:
        """Activate the wandb environment for the current step."""
        self._create_or_reuse_wandb_run()
        return super().activate()

    def deactivate(self) -> None:
        """Deactivate the wandb environment for the current step."""
        return super().deactivate()

    @property
    def wandb_project_name(self) -> str:
        """Returns the wandb project name for the current step."""
        return self._project_name

    @property
    def wandb_experiment_name(self) -> str:
        """Returns the wandb experiment name for the current step."""
        return self._experiment_name

    @property
    def wandb_run_name(self) -> str:
        """Returns the wandb run name for the current step."""
        return self._run_name

    @property
    def wandb_run(self) -> Optional[Any]:
        """Returns the wandb run for the current step."""
        return self._run
