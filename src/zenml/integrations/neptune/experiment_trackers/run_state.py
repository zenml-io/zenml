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
from zenml.integrations.constants import NEPTUNE
from zenml.utils.singleton import SingletonMetaClass

if TYPE_CHECKING:
    from neptune import Run

_INTEGRATION_VERSION_KEY = "source_code/integrations/zenml"


class InvalidExperimentTrackerSelected(Exception):
    """Raised if a Neptune run is fetched while using a different experiment tracker."""


class RunProvider(metaclass=SingletonMetaClass):
    """Singleton object used to store and persist a Neptune run state across the pipeline."""

    def __init__(self) -> None:
        """Initialize RunProvider. Called with no arguments."""
        self._active_run: Optional["Run"] = None
        self._project: Optional[str]
        self._run_name: Optional[str]
        self._token: Optional[str]
        self._tags: Optional[List[str]]

    @property
    def project(self) -> Optional[Any]:
        """Getter for project name.

        Returns:
            Name of the project passed to the RunProvider.
        """
        return self._project

    @project.setter
    def project(self, project: str) -> None:
        """Setter for project name.

        Args:
            project: Neptune project name
        """
        self._project = project

    @property
    def token(self) -> Optional[Any]:
        """Getter for API token.

        Returns:
            Neptune API token passed to the RunProvider.
        """
        return self._token

    @token.setter
    def token(self, token: str) -> None:
        """Setter for API token.

        Args:
            token: Neptune API token
        """
        self._token = token

    @property
    def run_name(self) -> Optional[Any]:
        """Getter for run name.

        Returns:
            Name of the pipeline run.
        """
        return self._run_name

    @run_name.setter
    def run_name(self, run_name: str) -> None:
        """Setter for run name.

        Args:
            run_name: name of the pipeline run
        """
        self._run_name = run_name

    @property
    def tags(self) -> Optional[Any]:
        """Getter for run tags.

        Returns:
            Tags associated with a Neptune run.
        """
        return self._tags

    @tags.setter
    def tags(self, tags: List[str]) -> None:
        """Setter for run tags.

        Args:
            tags: list of tags associated with a Neptune run
        """
        self._tags = tags

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

    def reset_active_run(self) -> None:
        """Resets the active run state to None."""
        self._active_run = None


def get_neptune_run() -> "Run":
    """Helper function to fetch an existing Neptune run or create a new one.

    Returns:
        Neptune run object

    Raises:
        InvalidExperimentTrackerSelected: when called while using an experiment tracker other than Neptune
    """
    client = Client()
    experiment_tracker = client.active_stack.experiment_tracker
    if experiment_tracker.flavor == NEPTUNE:  # type: ignore
        return experiment_tracker.run_state.active_run  # type: ignore
    raise InvalidExperimentTrackerSelected(
        "Fetching a Neptune run works only with the 'neptune' flavor of "
        "the experiment tracker. The flavor currently selected is %s"
        % experiment_tracker.flavor  # type: ignore
    )
