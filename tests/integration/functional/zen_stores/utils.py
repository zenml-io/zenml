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
from zenml.client import Client
from zenml.models import (
    PipelineRunFilterModel,
    RoleRequestModel,
    StepRunFilterModel,
    TeamRequestModel,
    UserRequestModel,
)
from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.utils.string_utils import random_str


@step
def constant_int_output_test_step() -> int:
    return 7


@step
def int_plus_one_test_step(input: int) -> int:
    return input + 1


@pipeline(name="connected_two_step_pipeline")
def connected_two_step_pipeline(step_1, step_2):
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2` that are connected."""
    step_2(step_1())


pipeline_instance = connected_two_step_pipeline(
    step_1=constant_int_output_test_step(),
    step_2=int_plus_one_test_step(),
)


class PipelineRunContext:
    """Context manager that creates pipeline runs and cleans them up afterwards."""

    def __init__(self, num_runs: int):
        self.num_runs = num_runs
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        for i in range(self.num_runs):
            pipeline_instance.run(
                run_name=f"sample_pipeline_run_{i}", unlisted=True
            )

        # persist which runs, steps and artifacts were produced, in case
        #  the test ends up deleting some or all of these, this allows for a
        #  thorough cleanup nonetheless
        self.runs = self.store.list_runs(
            PipelineRunFilterModel(name=f"startswith:sample_pipeline_run_")
        ).items
        self.steps = list()
        self.artifacts = list()
        for run in self.runs:
            self.steps += self.store.list_run_steps(
                StepRunFilterModel(pipeline_run_id=run.id)
            ).items
            for step in self.steps:
                self.artifacts += [a for a in step.output_artifacts.values()]
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for artifact in self.artifacts:
            try:
                self.store.delete_artifact(artifact.id)
            except KeyError:
                pass
        for run in self.runs:
            try:
                self.store.delete_run(run.id)
            except KeyError:
                pass


class UserContext:
    def __init__(self, user_name: str = "aria"):
        self.user_name = user_name
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_user = UserRequestModel(name=sample_name(self.user_name))
        self.created_user = self.store.create_user(new_user)
        return self.created_user

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.store.delete_user(self.created_user.id)


class TeamContext:
    def __init__(self, team_name: str = "arias_fanclub"):
        self.team_name = team_name
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_team = TeamRequestModel(name=sample_name(self.team_name))
        self.created_team = self.store.create_team(new_team)
        return self.created_team

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.store.delete_team(self.created_team.id)


class RoleContext:
    def __init__(self, role_name: str = "aria_tamer"):
        self.role_name = role_name
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_role = RoleRequestModel(
            name=sample_name(self.role_name), permissions=set()
        )
        self.created_role = self.store.create_role(new_role)
        return self.created_role

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.store.delete_role(self.created_role.id)


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}_{random_str(4)}"
