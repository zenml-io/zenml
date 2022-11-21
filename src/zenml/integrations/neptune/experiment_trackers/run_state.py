import functools
import hashlib
from typing import List

import neptune.new as neptune

from zenml.client import Client
from zenml.integrations.constants import NEPTUNE
from zenml.steps.base_step import BaseStepMeta


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


class NoActiveRunException(Exception):
    pass


class InvalidExperimentTrackerSelected(Exception):
    pass


@singleton
class RunProvider:
    def __init__(self):
        self._active_run = None
        self._project = None
        self._run_name = None
        self._token = None
        self._tags = None

    @property
    def project(self) -> str:
        return self._project

    @property
    def token(self) -> str:
        return self._token

    @property
    def run_name(self) -> str:
        return self._run_name

    @property
    def tags(self) -> List[str]:
        return self._tags

    @project.setter
    def project(self, project: str):
        self._project = project

    @token.setter
    def token(self, token: str):
        self._token = token

    @run_name.setter
    def run_name(self, run_name: str):
        self._run_name = run_name

    @tags.setter
    def tags(self, tags: List[str]):
        self._tags = tags

    @property
    def active_run(self) -> neptune.metadata_containers.Run:
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
    client = Client()
    experiment_tracker = client.active_stack.experiment_tracker
    if experiment_tracker.flavor == NEPTUNE:
        return experiment_tracker.run_state.active_run
    raise InvalidExperimentTrackerSelected(
        "Fetching neptune run works only with neptune flavor of"
        "experiment tracker selected. Current selection is %s"
        % experiment_tracker.flavor
    )


def neptune_step(step: BaseStepMeta):
    client = Client()
    experiment_tracker = client.active_stack.experiment_tracker.name

    @functools.wraps(step)
    def wrapper(*args, **kwargs):
        return step(*args, experiment_tracker=experiment_tracker, **kwargs)

    return wrapper
