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
from contextlib import contextmanager
from typing import ClassVar, Optional, Tuple

import wandb  # type: ignore[import]

from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.constants import WANDB
from zenml.logger import get_logger
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)


WANDB_API_KEY = "WANDB_API_KEY"


@register_stack_component_class
class WandbExperimentTracker(BaseExperimentTracker):
    """Stores wandb configuration options.

    ZenML should take care of configuring wandb for you, but should you still
    need access to the configuration inside your step you can do it using a
    step context:
    ```python
    from zenml.steps import StepContext

    @enable_wandb
    @step
    def my_step(context: StepContext, ...)
        context.stack.experiment_tracker  # get the tracking_uri etc. from here
    ```

    Attributes:
    """

    api_key: str
    entity: str
    project_name: str

    # Class Configuration
    FLAVOR: ClassVar[str] = WANDB

    def prepare_step_run(self) -> None:
        """Sets the wandb api key."""
        os.environ[WANDB_API_KEY] = self.api_key

    @contextmanager
    def configure_wandb(
        self,
        run_name: str,
        tags: Tuple[str] = (),
        settings: Optional[wandb.Settings] = None,
    ) -> None:
        try:
            logger.info(
                f"Initializing wandb with project name: {self.project_name}, "
                f"run_name: {run_name}, entity: {self.entity}."
            )
            wandb.init(
                project=self.project_name,
                name=run_name,
                entity=self.entity,
                settings=settings,
                tags=tags,
            )
            yield
        finally:
            wandb.finish()
