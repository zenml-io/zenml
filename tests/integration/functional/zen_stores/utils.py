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
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from tests.integration.functional.utils import sample_name
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ArtifactType, ExecutionStatus, StackComponentType
from zenml.models import (
    ArtifactFilterModel,
    ArtifactRequestModel,
    BaseFilterModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentUpdateModel,
    FlavorFilterModel,
    FlavorRequestModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunUpdateModel,
    PipelineUpdateModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleUpdateModel,
    StackRequestModel,
    StepRunFilterModel,
    TeamFilterModel,
    TeamRequestModel,
    TeamUpdateModel,
    UserFilterModel,
    UserRequestModel,
    UserUpdateModel,
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceUpdateModel,
)
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.page_model import Page
from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.zen_stores.base_zen_store import BaseZenStore


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
        self.pipeline_name = sample_name("sample_pipeline_run_")
        for i in range(self.num_runs):
            pipeline_instance.run(
                run_name=f"{self.pipeline_name}_{i}", unlisted=True
            )

        # persist which runs, steps and artifacts were produced, in case
        #  the test ends up deleting some or all of these, this allows for a
        #  thorough cleanup nonetheless
        self.runs = self.store.list_runs(
            PipelineRunFilterModel(name=f"startswith:{self.pipeline_name}")
        ).items
        self.steps = []
        self.artifacts = []
        for run in self.runs:
            self.steps += self.store.list_run_steps(
                StepRunFilterModel(pipeline_run_id=run.id)
            ).items
            for s in self.steps:
                self.artifacts += [a for a in s.output_artifacts.values()]
        return self.runs

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
    def __init__(self, user_name: str = "aria", login: bool = False):
        self.user_name = sample_name(user_name)
        self.client = Client()
        self.store = self.client.zen_store
        self.login = login

    def __enter__(self):
        new_user = UserRequestModel(name=self.user_name, password="abcd")
        self.created_user = self.store.create_user(new_user)

        if self.login:
            self.client.create_user_role_assignment(
                role_name_or_id="admin", user_name_or_id=self.created_user.id
            )
            self.original_config = GlobalConfiguration.get_instance()
            self.original_client = Client.get_instance()

            GlobalConfiguration._reset_instance()
            Client._reset_instance()
            self.client = Client()

            url = self.original_config.zen_store.url
            store_type = self.original_config.zen_store.type
            store_dict = {
                "url": url,
                "username": self.user_name,
                "password": "abcd",
            }
            store_config_class = BaseZenStore.get_store_config_class(
                store_type
            )
            store_config = store_config_class.parse_obj(store_dict)
            GlobalConfiguration().set_store(store_config)

        return self.created_user

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.login:
            GlobalConfiguration._reset_instance(self.original_config)
            Client._reset_instance(self.original_client)
            _ = Client().zen_store
        try:
            self.store.delete_user(self.created_user.id)
        except KeyError:
            pass


class StackContext:
    def __init__(
        self,
        components: Dict[StackComponentType, List[uuid.UUID]],
        stack_name: str = "aria",
        user_id: Optional[uuid.UUID] = None,
    ):
        self.stack_name = sample_name(stack_name)
        self.user_id = user_id
        self.components = components
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_stack = StackRequestModel(
            user=self.user_id if self.user_id else self.client.active_user.id,
            workspace=self.client.active_workspace.id,
            name=self.stack_name,
            components=self.components,
        )
        self.created_stack = self.store.create_stack(new_stack)
        return self.created_stack

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.store.delete_stack(self.created_stack.id)
        except KeyError:
            pass


class ComponentContext:
    def __init__(
        self,
        c_type: StackComponentType,
        config: Dict[str, Any],
        flavor: str,
        component_name: str = "aria",
        user_id: Optional[uuid.UUID] = None,
    ):
        self.component_name = sample_name(component_name)
        self.flavor = flavor
        self.component_type = c_type
        self.config = config
        self.user_id = user_id
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_component = ComponentRequestModel(
            user=self.user_id if self.user_id else self.client.active_user.id,
            workspace=self.client.active_workspace.id,
            name=self.component_name,
            type=self.component_type,
            flavor=self.flavor,
            configuration=self.config,
        )
        self.created_component = self.store.create_stack_component(
            new_component
        )
        return self.created_component

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.store.delete_stack_component(self.created_component.id)
        except KeyError:
            pass


class TeamContext:
    def __init__(self, team_name: str = "arias_fanclub"):
        self.team_name = sample_name(team_name)
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_team = TeamRequestModel(name=self.team_name)
        self.created_team = self.store.create_team(new_team)
        return self.created_team

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.store.delete_team(self.created_team.id),
        except KeyError:
            pass


class RoleContext:
    def __init__(self, role_name: str = "aria_tamer"):
        self.role_name = sample_name(role_name)
        self.client = Client()
        self.store = self.client.zen_store

    def __enter__(self):
        new_role = RoleRequestModel(name=self.role_name, permissions=set())
        self.created_role = self.store.create_role(new_role)
        return self.created_role

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.store.delete_role(self.created_role.id)
        except KeyError:
            pass


AnyRequestModel = TypeVar("AnyRequestModel", bound=BaseRequestModel)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


class CrudTestConfig(BaseModel):
    """Model to collect all methods pertaining to a given entity.

    Please Note: This implementation will only work for named entities,
    (entities with a `name` field)
    """

    create_model: "BaseRequestModel"
    update_model: Optional["BaseModel"]
    filter_model: Type[BaseFilterModel]
    entity_name: str

    @property
    def list_method(
        self,
    ) -> Callable[[BaseFilterModel], Page[AnyResponseModel]]:
        store = Client().zen_store
        return getattr(store, f"list_{self.entity_name}s")

    @property
    def get_method(self) -> Callable[[uuid.UUID], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, f"get_{self.entity_name}")

    @property
    def delete_method(self) -> Callable[[uuid.UUID], None]:
        store = Client().zen_store
        return getattr(store, f"delete_{self.entity_name}")

    @property
    def create_method(self) -> Callable[[AnyRequestModel], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, f"create_{self.entity_name}")

    @property
    def update_method(
        self,
    ) -> Callable[[uuid.UUID, BaseModel], AnyResponseModel]:
        store = Client().zen_store
        return getattr(store, f"update_{self.entity_name}")


workspace_crud_test_config = CrudTestConfig(
    create_model=WorkspaceRequestModel(name=sample_name("sample_workspace")),
    update_model=WorkspaceUpdateModel(
        name=sample_name("updated_sample_workspace")
    ),
    filter_model=WorkspaceFilterModel,
    entity_name="workspace",
)
user_crud_test_config = CrudTestConfig(
    create_model=UserRequestModel(name=sample_name("sample_user")),
    update_model=UserUpdateModel(name=sample_name("updated_sample_user")),
    filter_model=UserFilterModel,
    entity_name="user",
)
role_crud_test_config = CrudTestConfig(
    create_model=RoleRequestModel(
        name=sample_name("sample_role"), permissions=set()
    ),
    update_model=RoleUpdateModel(name=sample_name("updated_sample_role")),
    filter_model=RoleFilterModel,
    entity_name="role",
)
team_crud_test_config = CrudTestConfig(
    create_model=TeamRequestModel(name=sample_name("sample_team")),
    update_model=TeamUpdateModel(name=sample_name("updated_sample_team")),
    filter_model=TeamFilterModel,
    entity_name="team",
)
flavor_crud_test_config = CrudTestConfig(
    create_model=FlavorRequestModel(
        name=sample_name("sample_flavor"),
        type=StackComponentType.ORCHESTRATOR,
        integration="",
        source="",
        config_schema="",
        workspace=uuid.uuid4(),
    ),
    filter_model=FlavorFilterModel,
    entity_name="flavor",
)
component_crud_test_config = CrudTestConfig(
    create_model=ComponentRequestModel(
        name=sample_name("sample_component"),
        type=StackComponentType.ORCHESTRATOR,
        flavor="local",
        configuration={},
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    update_model=ComponentUpdateModel(
        name=sample_name("updated_sample_component")
    ),
    filter_model=ComponentFilterModel,
    entity_name="stack_component",
)
pipeline_crud_test_config = CrudTestConfig(
    create_model=PipelineRequestModel(
        name=sample_name("sample_pipeline"),
        spec=PipelineSpec(steps=[]),
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    update_model=PipelineUpdateModel(
        name=sample_name("updated_sample_pipeline")
    ),
    filter_model=PipelineFilterModel,
    entity_name="pipeline",
)
pipeline_run_crud_test_config = CrudTestConfig(
    create_model=PipelineRunRequestModel(
        id=uuid.uuid4(),
        name=sample_name("sample_pipeline_run"),
        status=ExecutionStatus.RUNNING,
        pipeline_configuration={},
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    update_model=PipelineRunUpdateModel(status=ExecutionStatus.COMPLETED),
    filter_model=PipelineRunFilterModel,
    entity_name="run",
)
artifact_crud_test_config = CrudTestConfig(
    create_model=ArtifactRequestModel(
        name=sample_name("sample_artifact"),
        data_type="",
        materializer="",
        type=ArtifactType.DATA,
        uri="",
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    filter_model=ArtifactFilterModel,
    entity_name="artifact",
)

# step_run_crud_test_config = CrudTestConfig(
#     create_model=StepRunRequestModel(
#         name=sample_name("sample_step_run"),
#         step=Step(
#             spec=StepSpec(source="", upstream_steps=[], inputs=[]),
#             config=StepConfiguration(name="sample_step_run")
#         ),
#         status=ExecutionStatus.RUNNING,
#         user=uuid.uuid4(),
#         workspace=uuid.uuid4(),
#         pipeline_run_id=uuid.uuid4()   # Pipeline run with id needs to exist
#     ),
#     update_model=StepRunUpdateModel(status=ExecutionStatus.COMPLETED),
#     filter_model=StepRunFilterModel,
#     entity_name="run_step",
# )


list_of_entities = [
    workspace_crud_test_config,
    user_crud_test_config,
    role_crud_test_config,
    team_crud_test_config,
    flavor_crud_test_config,
    component_crud_test_config,
    pipeline_crud_test_config,
    # step_run_crud_test_config,
    pipeline_run_crud_test_config,
    artifact_crud_test_config,
]
