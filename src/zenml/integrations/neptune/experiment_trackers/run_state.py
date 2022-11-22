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
"""Module containing objects allowing to store the state of neptune run across the project."""

import hashlib
from typing import List

import neptune.new as neptune

from zenml.client import Client
from zenml.integrations.constants import NEPTUNE
from zenml.utils.singleton import SingletonMetaClass


class InvalidExperimentTrackerSelected(Exception):
    """Raised if neptune run is fetched while using a different experiment tracker."""
    pass


class RunProvider(metaclass=SingletonMetaClass):
    """Singleton object used to store and persist neptune run state across the pipeline."""
    def __init__(self):
        """Initialize RunProvider. Called with no arguments."""
        self._active_run = None
        self._project = None
        self._run_name = None
        self._token = None
        self._tags = None

    @property
    def project(self) -> str:
        """Getter for project name.

        Returns:
            Name of the project fed to the RunProvider.
        """
        return self._project

    @property
    def token(self) -> str:
        """Getter for api token.

        Returns:
            Neptune API token fed to the RunProvider.
        """
        return self._token

    @property
    def run_name(self) -> str:
        """Getter for run name.

        Returns:
            Name of the pipeline run.
        """
        return self._run_name

    @property
    def tags(self) -> List[str]:
        """Getter for run tags.

        Returns:
            Tags associated with neptune run.
        """
        return self._tags

    @project.setter
    def project(self, project: str):
        """Setter for project name.

        Args:
            project: neptune project name
        """
        self._project = project

    @token.setter
    def token(self, token: str):
        """Setter for api token.

        Args:
            token: neptune API token
        """
        self._token = token

    @run_name.setter
    def run_name(self, run_name: str):
        """Setter for run name.

        Args:
            run_name: name of the pipeline run
        """
        self._run_name = run_name

    @tags.setter
    def tags(self, tags: List[str]):
        """Setter for run tags.

        Args:
            tags: list of tags associated with neptune run
        """
        self._tags = tags

    @property
    def active_run(self) -> neptune.metadata_containers.Run:
        """Either gets active neptune run or initializes a new one.

        Returns:
            Neptune run object
        """
        if self._active_run is None:
            run = neptune.init_run(
                project=self.project,
                api_token=self.token,
                custom_run_id=hashlib.md5(self.run_name.encode()).hexdigest(),
                tags=self.tags,
            )

            self._active_run = run
        return self._active_run


def get_neptune_run() -> neptune.metadata_containers.Run:
    """Helper function to fetch existing neptune run or create a new one.

    Returns:
        neptune run object

    Raises:
        InvalidExperimentTrackerSelected: when called while using an experiment tracker other than neptune
    """
    client = Client()
    experiment_tracker = client.active_stack.experiment_tracker
    if experiment_tracker.flavor == NEPTUNE:
        return experiment_tracker.run_state.active_run
    raise InvalidExperimentTrackerSelected(
        "Fetching neptune run works only with neptune flavor of"
        "experiment tracker selected. Current selection is %s"
        % experiment_tracker.flavor
    )
