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
"""Implementation of Neptune Experiment Tracker"""

from typing import TYPE_CHECKING, Any, Optional, Set, Type, cast

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
    BaseExperimentTrackerConfig,
)
from zenml.integrations.neptune.experiment_trackers.run_state import RunProvider
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo


class NeptuneExperimentTrackerConfig(BaseExperimentTrackerConfig):
    """Config for the Neptune experiment tracker.
    If attributes are left as None, neptune init_run
    will try to find the relevant values in the environment

        Attributes:
            project: name of the neptune project you want to log the metadata to
            api_token: your secret api key to neptune
    """

    project: Optional[str] = None
    api_token: Optional[str] = SecretField()


class NeptuneExperimentTrackerSettings(BaseSettings):
    """Settings for the Neptune experiment tracker.

        Attributes:
            tags: Tags for the neptune run.
    """

    tags: Set[str] = set()


class NeptuneExperimentTracker(BaseExperimentTracker):
    """Track experiments using neptune.ai"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the experiment tracker.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.run_state: RunProvider = RunProvider()

    @property
    def config(self) -> NeptuneExperimentTrackerConfig:
        """Returns the `NeptuneExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(NeptuneExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Neptune experiment tracker.

        Returns:
            The settings class.
        """
        return NeptuneExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Initializes neptune run and stores it in the run_state object.

        The run object can then be accessed later from other places e.g. step.
        """
        settings = cast(NeptuneExperimentTrackerSettings, self.get_settings(info))

        self.run_state.token = self.config.api_token
        self.run_state.project = self.config.project
        self.run_state.run_name = info.run_name
        self.run_state.tags = list(settings.tags)
