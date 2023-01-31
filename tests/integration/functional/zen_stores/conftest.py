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
import uuid
from typing import Callable, Optional, Type, TypeVar

from pydantic import BaseModel

from tests.integration.functional.zen_stores.utils import sample_name
from zenml.client import Client
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
    ProjectFilterModel,
    ProjectRequestModel,
    ProjectUpdateModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleUpdateModel,
    TeamFilterModel,
    TeamRequestModel,
    TeamUpdateModel,
    UserFilterModel,
    UserRequestModel,
    UserUpdateModel,
)
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
)
from zenml.models.page_model import Page

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


project_crud_test_config = CrudTestConfig(
    create_model=ProjectRequestModel(name=sample_name("sample_project")),
    update_model=ProjectUpdateModel(
        name=sample_name("updated_sample_project")
    ),
    filter_model=ProjectFilterModel,
    entity_name="project",
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
        user=uuid.uuid4(),
        project=uuid.uuid4(),
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
        project=uuid.uuid4(),
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
        project=uuid.uuid4(),
    ),
    update_model=PipelineUpdateModel(
        name=sample_name("updated_sample_pipeline")
    ),
    filter_model=PipelineFilterModel,
    entity_name="pipeline",
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
#         project=uuid.uuid4(),
#         pipeline_run_id=uuid.uuid4()   # Pipeline run with id needs to exist
#     ),
#     update_model=StepRunUpdateModel(status=ExecutionStatus.COMPLETED),
#     filter_model=StepRunFilterModel,
#     entity_name="run_step",
# )

pipeline_run_crud_test_config = CrudTestConfig(
    create_model=PipelineRunRequestModel(
        id=uuid.uuid4(),
        name=sample_name("sample_pipeline_run"),
        status=ExecutionStatus.COMPLETED,
        pipeline_configuration={},
        user=uuid.uuid4(),
        project=uuid.uuid4(),
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
        project=uuid.uuid4(),
    ),
    filter_model=ArtifactFilterModel,
    entity_name="artifact",
)

list_of_entities = [
    project_crud_test_config,
    user_crud_test_config,
    role_crud_test_config,
    team_crud_test_config,
    flavor_crud_test_config,
    component_crud_test_config,
    # stack_crud_test_config,
    pipeline_crud_test_config,
    # step_run_crud_test_config,
    pipeline_run_crud_test_config,
    artifact_crud_test_config,
]
