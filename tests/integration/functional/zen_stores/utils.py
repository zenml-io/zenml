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
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field, SecretStr

from tests.integration.functional.utils import sample_name
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.store_config import StoreConfiguration
from zenml.enums import (
    ArtifactType,
    SecretScope,
    StackComponentType,
)
from zenml.models import (
    ArtifactFilterModel,
    ArtifactRequestModel,
    AuthenticationMethodModel,
    BaseFilterModel,
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryUpdateModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentUpdateModel,
    FlavorFilterModel,
    FlavorRequestModel,
    ModelFilterModel,
    ModelRequestModel,
    ModelUpdateModel,
    ModelVersionRequestModel,
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineUpdateModel,
    ResourceTypeModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleUpdateModel,
    SecretFilterModel,
    SecretRequestModel,
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
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
from zenml.service_connectors.service_connector import AuthenticationConfig
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.steps import step
from zenml.utils.string_utils import random_str


@step
def constant_int_output_test_step() -> int:
    logging.info("log")
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

    def __init__(self, num_runs: int, enable_step_logs: bool = True):
        self.num_runs = num_runs
        self.client = Client()
        self.store = self.client.zen_store
        self.enable_step_logs = enable_step_logs

    def __enter__(self):
        self.pipeline_name = sample_name("sample_pipeline_run_")
        for i in range(self.num_runs):
            pipeline_instance.run(
                run_name=f"{self.pipeline_name}_{i}",
                unlisted=True,
                enable_step_logs=self.enable_step_logs,
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
                self.artifacts += [a for a in s.outputs.values()]
        return self.runs

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for run in self.runs:
            try:
                self.client.delete_pipeline_run(run.id)
            except KeyError:
                pass
        for artifact in self.artifacts:
            try:
                self.client.delete_artifact(artifact.id)
            except KeyError:
                pass


class UserContext:
    def __init__(
        self,
        user_name: Optional[str] = "aria",
        password: Optional[str] = None,
        login: bool = False,
        existing_user: bool = False,
        delete: bool = True,
    ):
        if existing_user:
            self.user_name = user_name
        else:
            self.user_name = sample_name(user_name)
        self.client = Client()
        self.store = self.client.zen_store
        self.login = login
        self.password = password or random_str(32)
        self.existing_user = existing_user
        self.delete = delete

    def __enter__(self):
        if not self.existing_user:
            new_user = UserRequestModel(
                name=self.user_name, password=self.password
            )
            self.created_user = self.store.create_user(new_user)
        else:
            self.created_user = self.store.get_user(self.user_name)

        if self.login or self.existing_user:
            if not self.existing_user:
                self.client.create_user_role_assignment(
                    role_name_or_id="admin",
                    user_name_or_id=self.created_user.id,
                )
            self.original_config = GlobalConfiguration.get_instance()
            self.original_client = Client.get_instance()

            GlobalConfiguration._reset_instance()
            Client._reset_instance()
            self.client = Client()
            store_config = StoreConfiguration(
                url=self.original_config.store.url,
                type=self.original_config.store.type,
                username=self.user_name,
                password=self.password,
                secrets_store=self.original_config.store.secrets_store,
            )
            GlobalConfiguration().set_store(config=store_config)
        return self.created_user

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.login or self.existing_user:
            GlobalConfiguration._reset_instance(self.original_config)
            Client._reset_instance(self.original_client)
            _ = Client().zen_store
        if not self.existing_user and self.delete:
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


class WorkspaceContext:
    def __init__(
        self,
        workspace_name: str = "super_axl",
        create: bool = True,
        activate: bool = False,
    ):
        self.workspace_name = (
            sample_name(workspace_name) if create else workspace_name
        )
        self.client = Client()
        self.store = self.client.zen_store
        self.create = create
        self.activate = activate

    def __enter__(self):
        if self.create:
            new_workspace = WorkspaceRequestModel(name=self.workspace_name)
            self.workspace = self.store.create_workspace(new_workspace)
        else:
            self.workspace = self.store.get_workspace(self.workspace_name)

        if self.activate:
            self.original_workspace = self.client.active_workspace
            self.client.set_active_workspace(self.workspace.id)
        return self.workspace

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.activate:
            self.client.set_active_workspace(self.original_workspace.id)
        if self.create:
            try:
                self.store.delete_workspace(self.workspace.id)
            except KeyError:
                pass


class SecretContext:
    def __init__(
        self,
        secret_name: Optional[str] = None,
        scope: SecretScope = SecretScope.WORKSPACE,
        values: Dict[str, str] = {
            "sleep": "yes",
            "food": "hell yeah",
            "bath": "NO!",
        },
        user_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        delete: bool = True,
    ):
        self.secret_name = (
            sample_name("axls-secrets") if not secret_name else secret_name
        )
        self.scope = scope
        self.values = values
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.client = Client()
        self.store = self.client.zen_store
        self.delete = delete

    def __enter__(self):
        new_secret = SecretRequestModel(
            name=self.secret_name,
            scope=self.scope,
            values=self.values,
            user=self.user_id or self.client.active_user.id,
            workspace=self.workspace_id or self.client.active_workspace.id,
        )
        self.created_secret = self.store.create_secret(new_secret)
        return self.created_secret

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.delete:
            try:
                self.store.delete_secret(self.created_secret.id)
            except KeyError:
                pass


class CodeRepositoryContext:
    def __init__(
        self,
        user_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        delete: bool = True,
    ):
        self.code_repo_name = sample_name("code_repo")
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.client = Client()
        self.store = self.client.zen_store
        self.delete = delete

    def __enter__(self):
        request = CodeRepositoryRequestModel(
            name=self.code_repo_name,
            config={},
            source={
                "module": "tests.unit.pipelines.test_build_utils",
                "attribute": "StubCodeRepository",
                "type": "user",
            },
            user=self.user_id or self.client.active_user.id,
            workspace=self.workspace_id or self.client.active_workspace.id,
        )

        self.repo = self.store.create_code_repository(request)
        return self.repo

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.delete:
            try:
                self.store.delete_code_repository(self.repo.id)
            except KeyError:
                pass


class ServiceConnectorContext:
    def __init__(
        self,
        connector_type: str,
        auth_method: str,
        resource_types: List[str],
        name: Optional[str] = None,
        resource_id: Optional[str] = None,
        configuration: Optional[Dict[str, str]] = None,
        secrets: Optional[Dict[str, Optional[SecretStr]]] = None,
        expires_at: Optional[datetime] = None,
        expiration_seconds: Optional[int] = None,
        user_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        is_shared: bool = False,
        labels: Optional[Dict[str, str]] = None,
        client: Optional[Client] = None,
        delete: bool = True,
    ):
        self.name = name or sample_name("connect-or")
        self.connector_type = connector_type
        self.auth_method = auth_method
        self.resource_types = resource_types
        self.resource_id = resource_id
        self.configuration = configuration
        self.secrets = secrets
        self.expires_at = expires_at
        self.expiration_seconds = expiration_seconds
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.is_shared = is_shared
        self.labels = labels
        self.client = client or Client()
        self.store = self.client.zen_store
        self.delete = delete

    def __enter__(self):
        request = ServiceConnectorRequestModel(
            name=self.name,
            connector_type=self.connector_type,
            auth_method=self.auth_method,
            resource_types=self.resource_types,
            resource_id=self.resource_id,
            configuration=self.configuration or {},
            secrets=self.secrets or {},
            expires_at=self.expires_at,
            expiration_seconds=self.expiration_seconds,
            is_shared=self.is_shared,
            labels=self.labels or {},
            user=self.user_id or self.client.active_user.id,
            workspace=self.workspace_id or self.client.active_workspace.id,
        )

        self.connector = self.store.create_service_connector(request)
        return self.connector

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.delete:
            try:
                self.store.delete_service_connector(self.connector.id)
            except KeyError:
                pass


class ModelVersionContext:
    def __init__(
        self,
        create_version: bool = False,
        create_artifacts: int = 0,
        create_prs: int = 0,
    ):
        client = Client()
        self.workspace = client.active_workspace.id
        self.user = client.active_user.id
        self.model = "su_model"
        self.model_version = "2.0.0"

        self.create_version = create_version
        self.create_artifacts = create_artifacts
        self.artifacts = []
        self.create_prs = create_prs
        self.prs = []
        self.deployments = []

    def __enter__(self):
        client = Client()
        ws = client.get_workspace(self.workspace)
        user = client.get_user(self.user)
        stack = client.active_stack
        try:
            model = client.get_model(self.model)
        except KeyError:
            model = client.create_model(
                ModelRequestModel(
                    name=self.model, user=user.id, workspace=ws.id
                )
            )
        if self.create_version:
            try:
                mv = client.get_model_version(self.model, self.model_version)
            except KeyError:
                mv = client.create_model_version(
                    ModelVersionRequestModel(
                        user=user.id,
                        workspace=ws.id,
                        model=model.id,
                        name=self.model_version,
                    )
                )

        for _ in range(self.create_artifacts):
            self.artifacts.append(
                client.zen_store.create_artifact(
                    ArtifactRequestModel(
                        name=sample_name("sample_artifact"),
                        data_type="module.class",
                        materializer="module.class",
                        type=ArtifactType.DATA,
                        uri="",
                        user=user.id,
                        workspace=ws.id,
                    )
                )
            )
        for _ in range(self.create_prs):
            deployment = client.zen_store.create_deployment(
                PipelineDeploymentRequestModel(
                    user=user.id,
                    workspace=ws.id,
                    stack=stack.id,
                    run_name_template="",
                    pipeline_configuration={"name": "pipeline_name"},
                    client_version="0.12.3",
                    server_version="0.12.3",
                ),
            )
            self.deployments.append(deployment)
            self.prs.append(
                client.zen_store.create_run(
                    PipelineRunRequestModel(
                        id=uuid.uuid4(),
                        name=sample_name("sample_pipeline_run"),
                        status="running",
                        config=PipelineConfiguration(name="aria_pipeline"),
                        user=user.id,
                        workspace=ws.id,
                        deployment=deployment.id,
                    )
                )
            )
        if self.create_version:
            if self.create_artifacts:
                return mv, self.artifacts
            if self.create_prs:
                return mv, self.prs
            else:
                return mv
        else:
            if self.create_artifacts:
                return model, self.artifacts
            if self.create_prs:
                return model, self.prs
            else:
                return model

    def __exit__(self, exc_type, exc_value, exc_traceback):
        client = Client()
        try:
            client.delete_model(self.model)
        except KeyError:
            pass
        for artifact in self.artifacts:
            client.delete_artifact(artifact.id)
        for run in self.prs:
            client.zen_store.delete_run(run.id)
        for deployment in self.deployments:
            client.delete_deployment(str(deployment.id))


class CatClawMarks(AuthenticationConfig):
    """Cat claw marks authentication credentials."""

    paw: SecretStr = Field(
        title="Paw",
    )
    hiding_spot: Optional[SecretStr] = Field(
        default=None,
        title="Hiding spot",
    )
    color: Optional[str] = Field(
        default=None,
        title="Cat color.",
    )
    name: str = Field(
        title="Cat name.",
    )


class CatVoicePrint(AuthenticationConfig):
    """Cat voice print authentication credentials."""

    secret_word: SecretStr = Field(
        title="Secret word",
    )
    hiding_spot: Optional[SecretStr] = Field(
        default=None,
        title="Hiding spot",
    )
    color: Optional[str] = Field(
        default=None,
        title="Cat color.",
    )
    name: str = Field(
        title="Cat name.",
    )


class ServiceConnectorTypeContext:
    def __init__(
        self,
        connector_type: Optional[str] = None,
        resource_type_one: Optional[str] = None,
        resource_type_two: Optional[str] = None,
        delete: bool = True,
    ):
        self.connector_type = connector_type
        self.resource_type_one = resource_type_one
        self.resource_type_two = resource_type_two
        self.delete = delete

    def __enter__(self):
        self.connector_type_spec = ServiceConnectorTypeModel(
            name="Cat service connector",
            connector_type=self.connector_type or sample_name("cat'o'matic"),
            auth_methods=[
                AuthenticationMethodModel(
                    name="Claw marks authentication",
                    auth_method="claw-marks",
                    config_class=CatClawMarks,
                ),
                AuthenticationMethodModel(
                    name="Voice print authentication",
                    auth_method="voice-print",
                    config_class=CatVoicePrint,
                ),
            ],
            resource_types=[
                ResourceTypeModel(
                    name="Cat scratches",
                    resource_type=self.resource_type_one
                    or sample_name("scratch"),
                    auth_methods=["claw-marks", "voice-print"],
                    supports_instances=True,
                ),
                ResourceTypeModel(
                    name="Cat purrs",
                    resource_type=self.resource_type_two
                    or sample_name("purr"),
                    auth_methods=["claw-marks", "voice-print"],
                    supports_instances=False,
                ),
            ],
        )

        service_connector_registry.register_service_connector_type(
            self.connector_type_spec
        )

        return self.connector_type_spec

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.delete:
            try:
                del service_connector_registry.service_connector_types[
                    self.connector_type
                ]
            except KeyError:
                pass


AnyRequestModel = TypeVar("AnyRequestModel", bound=BaseRequestModel)
AnyResponseModel = TypeVar("AnyResponseModel", bound=BaseResponseModel)


class CrudTestConfig(BaseModel):
    """Model to collect all methods pertaining to a given entity."""

    create_model: "BaseRequestModel"
    update_model: Optional["BaseModel"]
    filter_model: Type[BaseFilterModel]
    entity_name: str

    @property
    def list_method(
        self,
    ) -> Callable[[BaseFilterModel], Page[AnyResponseModel]]:
        store = Client().zen_store
        if self.entity_name.endswith("y"):
            method_name = f"list_{self.entity_name[:-1]}ies"
        else:
            method_name = f"list_{self.entity_name}s"
        return getattr(store, method_name)

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
        version="1",
        version_hash="abc123",
    ),
    update_model=PipelineUpdateModel(
        name=sample_name("updated_sample_pipeline")
    ),
    filter_model=PipelineFilterModel,
    entity_name="pipeline",
)
# pipeline_run_crud_test_config = CrudTestConfig(
#     create_model=PipelineRunRequestModel(
#         id=uuid.uuid4(),
#         deployment=uuid.uuid4(), # deployment has to exist first
#         pipeline=uuid.uuid4(),
#         name=sample_name("sample_pipeline_run"),
#         status=ExecutionStatus.RUNNING,
#         config=PipelineConfiguration(name="aria_pipeline"),
#         user=uuid.uuid4(),
#         workspace=uuid.uuid4(),
#     ),
#     update_model=PipelineRunUpdateModel(status=ExecutionStatus.COMPLETED),
#     filter_model=PipelineRunFilterModel,
#     entity_name="run",
# )
artifact_crud_test_config = CrudTestConfig(
    create_model=ArtifactRequestModel(
        name=sample_name("sample_artifact"),
        data_type="module.class",
        materializer="module.class",
        type=ArtifactType.DATA,
        uri="",
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    filter_model=ArtifactFilterModel,
    entity_name="artifact",
)
secret_crud_test_config = CrudTestConfig(
    create_model=SecretRequestModel(
        name=sample_name("sample_secret"),
        values={"key": "value"},
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
    ),
    filter_model=SecretFilterModel,
    entity_name="secret",
)
build_crud_test_config = CrudTestConfig(
    create_model=PipelineBuildRequestModel(
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
        images={},
        is_local=False,
        contains_code=True,
    ),
    filter_model=PipelineBuildFilterModel,
    entity_name="build",
)
deployment_crud_test_config = CrudTestConfig(
    create_model=PipelineDeploymentRequestModel(
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
        stack=uuid.uuid4(),
        run_name_template="template",
        pipeline_configuration={"name": "pipeline_name"},
        client_version="0.12.3",
        server_version="0.12.3",
    ),
    filter_model=PipelineDeploymentFilterModel,
    entity_name="deployment",
)
code_repository_crud_test_config = CrudTestConfig(
    create_model=CodeRepositoryRequestModel(
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
        name=sample_name("sample_code_repository"),
        config={},
        source={"module": "module", "type": "user"},
    ),
    update_model=CodeRepositoryUpdateModel(
        name=sample_name("updated_sample_code_repository")
    ),
    filter_model=CodeRepositoryFilterModel,
    entity_name="code_repository",
)
service_connector_crud_test_config = CrudTestConfig(
    create_model=ServiceConnectorRequestModel(
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
        name=sample_name("sample_service_connector"),
        connector_type="docker",
        auth_method="password",
        configuration=dict(
            username="user",
            password="password",
        ),
    ),
    update_model=ServiceConnectorUpdateModel(
        name=sample_name("updated_sample_service_connector"),
    ),
    filter_model=ServiceConnectorFilterModel,
    entity_name="service_connector",
)
model_crud_test_config = CrudTestConfig(
    create_model=ModelRequestModel(
        user=uuid.uuid4(),
        workspace=uuid.uuid4(),
        name="super_model",
        license="who cares",
        description="cool stuff",
        audience="world",
        use_cases="all",
        limitations="none",
        trade_offs="secret",
        ethics="all good",
        tags=["cool", "stuff"],
    ),
    update_model=ModelUpdateModel(
        name=sample_name("updated_sample_service_connector"),
        description="new_description",
    ),
    filter_model=ModelFilterModel,
    entity_name="model",
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
    # pipeline_run_crud_test_config,
    artifact_crud_test_config,
    secret_crud_test_config,
    build_crud_test_config,
    deployment_crud_test_config,
    code_repository_crud_test_config,
    service_connector_crud_test_config,
    model_crud_test_config,
]
