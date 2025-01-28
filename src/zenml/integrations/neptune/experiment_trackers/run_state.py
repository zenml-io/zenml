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
"""Contains objects that create a Neptune run and store its state throughout the pipeline."""

from hashlib import md5
from typing import TYPE_CHECKING, Any, List, Optional

import neptune

import zenml
from zenml.client import Client
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from neptune import Run

_INTEGRATION_VERSION_KEY = "source_code/integrations/zenml"


class RunProvider(metaclass=SingletonMetaClass):
    """Singleton object used to store and persist a Neptune run state across the pipeline."""

    def __init__(self) -> None:
        """Initialize RunProvider. Called with no arguments."""
        self._active_run: Optional["Run"] = None
        self._project: Optional[str] = None
        self._run_name: Optional[str] = None
        self._token: Optional[str] = None
        self._tags: Optional[List[str]] = None
        self._initialized = False

    def initialize(
        self,
        project: Optional[str] = None,
        token: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Initialize the run state.

        Args:
            project: The neptune project.
            token: The neptune token.
            run_name: The neptune run name.
            tags: Tags for the neptune run.
        """
        self._project = project
        self._token = token
        self._run_name = run_name
        self._tags = tags
        self._initialized = True

    @property
    def project(self) -> Optional[Any]:
        """Getter for project name.

        Returns:
            Name of the project passed to the RunProvider.
        """
        return self._project

    @property
    def token(self) -> Optional[Any]:
        """Getter for API token.

        Returns:
            Neptune API token passed to the RunProvider.
        """
        return self._token

    @property
    def run_name(self) -> Optional[Any]:
        """Getter for run name.

        Returns:
            Name of the pipeline run.
        """
        return self._run_name

    @property
    def tags(self) -> Optional[Any]:
        """Getter for run tags.

        Returns:
            Tags associated with a Neptune run.
        """
        return self._tags

    @property
    def initialized(self) -> bool:
        """If the run state is initialized.

        Returns:
            If the run state is initialized.
        """
        return self._initialized

    @property
    def active_run(self) -> "Run":
        """Initializes a new neptune run every time it is called.

        The run is closed and the active run state is set to stopped
        after each step is completed.

        Returns:
            Neptune run object
        """
        if self._active_run is None:
            run = neptune.init_run(
                project=self.project,
                api_token=self.token,
                custom_run_id=md5(self.run_name.encode()).hexdigest(),  # type: ignore  # nosec
                tags=self.tags,
            )
            run[_INTEGRATION_VERSION_KEY] = zenml.__version__
            self._active_run = run
        return self._active_run

    def reset(self) -> None:
        """Reset the run state."""
        self._active_run = None
        self._project = None
        self._run_name = None
        self._token = None
        self._tags = None
        self._initialized = False


def get_neptune_run() -> "Run":
    """Helper function to fetch an existing Neptune run or create a new one.

    Returns:
        Neptune run object

    Raises:
        RuntimeError: When unable to fetch the active neptune run.
    """
    from zenml.integrations.neptune.experiment_trackers import (
        NeptuneExperimentTracker,
    )

    experiment_tracker = Client().active_stack.experiment_tracker

    if not experiment_tracker:
        raise RuntimeError(
            "Unable to get neptune run: Missing experiment tracker in the "
            "active stack."
        )

    if not isinstance(experiment_tracker, NeptuneExperimentTracker):
        raise RuntimeError(
            "Unable to get neptune run: Experiment tracker in the active "
            f"stack ({experiment_tracker.flavor}) is not a neptune experiment "
            "tracker."
        )

    run_state = experiment_tracker.run_state
    if not run_state.initialized:
        raise RuntimeError(
            "Unable to get neptune run: The experiment tracker has not been "
            "initialized. To solve this, make sure you use the experiment "
            "tracker in your step. See "
            "https://docs.zenml.io/stack-components/experiment-trackers/neptune#how-do-you-use-it "
            "for more information."
        )

    return experiment_tracker.run_state.active_run
