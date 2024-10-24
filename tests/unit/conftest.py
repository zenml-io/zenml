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
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import pytest

from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import StepConfiguration, StepSpec
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
    BaseContainerRegistryConfig,
)
from zenml.enums import ArtifactType, ExecutionStatus
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import (
    ArtifactResponse,
    ArtifactResponseBody,
    ArtifactResponseMetadata,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionResponseBody,
    ArtifactVersionResponseMetadata,
    CodeRepositoryResponse,
    CodeRepositoryResponseBody,
    CodeRepositoryResponseMetadata,
    PipelineBuildResponse,
    PipelineBuildResponseBody,
    PipelineBuildResponseMetadata,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineDeploymentResponseBody,
    PipelineDeploymentResponseMetadata,
    PipelineResponse,
    PipelineResponseBody,
    PipelineResponseMetadata,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunResponseBody,
    PipelineRunResponseMetadata,
    PipelineRunResponseResources,
    StepRunRequest,
    StepRunResponse,
    StepRunResponseBody,
    StepRunResponseMetadata,
    StepRunResponseResources,
    UserResponse,
    UserResponseBody,
    UserResponseMetadata,
    WorkspaceResponse,
    WorkspaceResponseBody,
    WorkspaceResponseMetadata,
)
from zenml.models.v2.core.service import (
    ServiceResponse,
    ServiceResponseBody,
    ServiceResponseMetadata,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.pipelines import pipeline
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.services.service_status import ServiceState
from zenml.services.service_type import ServiceType
from zenml.stack.stack import Stack
from zenml.stack.stack_component import (
    StackComponentConfig,
    StackComponentType,
)
from zenml.step_operators import BaseStepOperator, BaseStepOperatorConfig
from zenml.steps import StepContext, step
from zenml.steps.entrypoint_function_utils import StepArtifact


@pytest.fixture
def local_stack():
    """Returns a local stack with local orchestrator and artifact store."""
    orchestrator = LocalOrchestrator(
        name="",
        id=uuid4(),
        config=StackComponentConfig(),
        flavor="default",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    artifact_store = LocalArtifactStore(
        name="",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="default",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    return Stack(
        id=uuid4(),
        name="",
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )


@pytest.fixture
def local_orchestrator():
    """Returns a local orchestrator."""
    return LocalOrchestrator(
        name="",
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def local_artifact_store():
    """Fixture that creates a local artifact store for testing."""
    return LocalArtifactStore(
        name="",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def local_container_registry():
    """Fixture that creates a local container registry for testing."""
    return BaseContainerRegistry(
        name="",
        id=uuid4(),
        config=BaseContainerRegistryConfig(uri="localhost:5000"),
        flavor="default",
        type=StackComponentType.CONTAINER_REGISTRY,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def remote_container_registry():
    """Fixture that creates a remote container registry for testing."""
    return BaseContainerRegistry(
        name="",
        id=uuid4(),
        config=BaseContainerRegistryConfig(uri="gcr.io/my-project"),
        flavor="gcp",
        type=StackComponentType.CONTAINER_REGISTRY,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def sample_step_operator() -> BaseStepOperator:
    """Fixture that creates a stub step operator for testing."""

    class StubStepOperator(BaseStepOperator):
        def launch(self, info, entrypoint_command) -> None:
            pass

    return StubStepOperator(
        name="",
        id=uuid4(),
        config=BaseStepOperatorConfig(),
        flavor="stub",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@step
def _empty_step() -> None:
    """Empty step for testing."""


@pytest.fixture
def empty_step():
    """Pytest fixture that returns an empty (no input, no output) step."""
    return _empty_step.copy()


@pytest.fixture
def generate_empty_steps():
    """Pytest fixture that returns a function that generates multiple empty steps."""

    def _generate_empty_steps(count: int):
        output = []

        for i in range(count):

            @step(name=f"step_{i}")
            def _step_function() -> None:
                pass

            output.append(_step_function)

        return output

    return _generate_empty_steps


@pytest.fixture
def one_step_pipeline():
    """Pytest fixture that returns a pipeline which takes a single step named `step_`."""

    def _wrapper(step_):
        @pipeline
        def _pipeline():
            step_()

        return _pipeline

    return _wrapper


@pytest.fixture
def unconnected_two_step_pipeline():
    """Pytest fixture that returns a pipeline which takes two steps `step_1` and `step_2`. The steps are not connected to each other."""

    def _wrapper(step_1, step_2):
        @pipeline
        def _pipeline():
            step_1()
            step_2()

        return _pipeline

    return _wrapper


@step
def _int_output_step() -> int:
    return 1


@pytest.fixture
def int_step_output():
    return StepArtifact(
        invocation_id="id",
        output_name="output_name",
        annotation=int,
        pipeline=Pipeline(name="test_pipeline", entrypoint=lambda: None),
    )


@pytest.fixture
def step_with_two_int_inputs():
    @step
    def _step(input_1: int, input_2: int) -> None:
        pass

    return _step


@pytest.fixture
def step_context_with_no_output(
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> StepContext:
    StepContext._clear()
    return StepContext(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        output_materializers={},
        output_artifact_uris={},
        output_artifact_configs={},
    )


@pytest.fixture
def step_context_with_single_output(
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> StepContext:
    materializers = {"output_1": (BaseMaterializer,)}
    artifact_uris = {"output_1": ""}
    artifact_configs = {"output_1": None}
    StepContext._clear()
    return StepContext(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        output_materializers=materializers,
        output_artifact_uris=artifact_uris,
        output_artifact_configs=artifact_configs,
    )


@pytest.fixture
def step_context_with_two_outputs(
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
) -> StepContext:
    materializers = {
        "output_1": (BaseMaterializer,),
        "output_2": (BaseMaterializer,),
    }
    artifact_uris = {
        "output_1": "",
        "output_2": "",
    }
    artifact_configs = {"output_1": None, "output_2": None}

    StepContext._clear()
    return StepContext(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        output_materializers=materializers,
        output_artifact_uris=artifact_uris,
        output_artifact_configs=artifact_configs,
    )


@pytest.fixture
def sample_user_model() -> UserResponse:
    """Return a sample user model for testing purposes."""
    return UserResponse(
        id=uuid4(),
        name="axl",
        body=UserResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            is_service_account=False,
            is_admin=True,
        ),
        metadata=UserResponseMetadata(),
    )


@pytest.fixture
def sample_workspace_model() -> WorkspaceResponse:
    """Return a sample workspace model for testing purposes."""
    return WorkspaceResponse(
        id=uuid4(),
        name="axl",
        body=WorkspaceResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
        ),
        metadata=WorkspaceResponseMetadata(),
    )


@pytest.fixture
def sample_step_request_model() -> StepRunRequest:
    """Return a sample step model for testing purposes."""
    spec = StepSpec.model_validate(
        {
            "source": "module.step_class",
            "upstream_steps": [],
            "inputs": {},
        }
    )
    config = StepConfiguration.model_validate(
        {"name": "step_name", "enable_cache": True}
    )

    return StepRunRequest(
        name="sample_step",
        pipeline_run_id=uuid4(),
        status=ExecutionStatus.COMPLETED,
        spec=spec,
        config=config,
        workspace=uuid4(),
        user=uuid4(),
        deployment=uuid4(),
    )


@pytest.fixture
def sample_step_run(create_step_run) -> StepRunResponse:
    """Return a sample step response model for testing purposes."""
    return create_step_run()


@pytest.fixture
def sample_pipeline_run(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> PipelineRunResponse:
    """Return sample pipeline run view for testing purposes."""
    return PipelineRunResponse(
        id=uuid4(),
        name="sample_run_name",
        body=PipelineRunResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_user_model,
            status=ExecutionStatus.COMPLETED,
            tags=[],
        ),
        metadata=PipelineRunResponseMetadata(
            workspace=sample_workspace_model,
            config=PipelineConfiguration(name="aria_pipeline"),
            is_templatable=False,
        ),
        resources=PipelineRunResponseResources(tags=[]),
    )


@pytest.fixture
def sample_pipeline_deployment_request_model() -> PipelineDeploymentRequest:
    """Return sample pipeline deployment request for testing purposes."""
    return PipelineDeploymentRequest(
        user=uuid4(),
        workspace=uuid4(),
        run_name_template="aria-blupus",
        pipeline_configuration=PipelineConfiguration(name="axls-pipeline"),
        client_version="0.12.3",
        server_version="0.12.3",
        stack=uuid4(),
    )


@pytest.fixture
def sample_pipeline_run_request_model() -> PipelineRunRequest:
    """Return sample pipeline run view for testing purposes."""
    return PipelineRunRequest(
        name="sample_run_name",
        config=PipelineConfiguration(name="aria_pipeline"),
        num_steps=1,
        status=ExecutionStatus.COMPLETED,
        user=uuid4(),
        workspace=uuid4(),
        deployment=uuid4(),
        pipeline=uuid4(),
    )


@pytest.fixture
def sample_artifact_model() -> ArtifactResponse:
    """Return a sample artifact model for testing purposes."""
    return ArtifactResponse(
        id=uuid4(),
        name="sample_artifact",
        body=ArtifactResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            tags=[],
        ),
        metadata=ArtifactResponseMetadata(
            has_custom_name=True,
        ),
    )


@pytest.fixture
def sample_artifact_version_model(
    sample_workspace_model, sample_user_model, sample_artifact_model
) -> ArtifactVersionResponse:
    """Return a sample artifact version model for testing purposes."""
    return ArtifactVersionResponse(
        id=uuid4(),
        body=ArtifactVersionResponseBody(
            artifact=sample_artifact_model,
            version="1",
            user=sample_user_model,
            created=datetime.now(),
            updated=datetime.now(),
            uri="sample_uri",
            type=ArtifactType.DATA,
            materializer="sample_module.sample_materializer",
            data_type="sample_module.sample_data_type",
            tags=[],
        ),
        metadata=ArtifactVersionResponseMetadata(
            workspace=sample_workspace_model,
        ),
    )


@pytest.fixture
def sample_artifact_request_model() -> ArtifactVersionRequest:
    """Return a sample artifact model for testing purposes."""
    return ArtifactVersionRequest(
        name="sample_artifact",
        version=1,
        uri="sample_uri",
        type=ArtifactType.DATA,
        materializer="sample_materializer",
        data_type="sample_data_type",
        workspace=uuid4(),
        user=uuid4(),
    )


@pytest.fixture
def create_step_run(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> Callable[..., StepRunResponse]:
    """Fixture that returns a function which can be used to create a
    customizable StepRunResponseModel."""

    def f(
        step_run_name: str = "step_run_name",
        step_name: str = "step_name",
        outputs: Optional[Dict[str, Any]] = None,
        output_artifacts: Optional[Dict[str, ArtifactVersionResponse]] = None,
        **kwargs: Any,
    ) -> StepRunResponse:
        spec = StepSpec.model_validate(
            {"source": "module.step_class", "upstream_steps": []}
        )
        config = StepConfiguration.model_validate(
            {
                "name": step_name,
                "outputs": outputs or {},
            }
        )
        return StepRunResponse(
            id=uuid4(),
            name=step_run_name,
            body=StepRunResponseBody(
                status=ExecutionStatus.COMPLETED,
                created=datetime.now(),
                updated=datetime.now(),
                user=sample_user_model,
                outputs=output_artifacts or {},
            ),
            metadata=StepRunResponseMetadata(
                pipeline_run_id=uuid4(),
                deployment_id=uuid4(),
                spec=spec,
                config=config,
                workspace=sample_workspace_model,
                **kwargs,
            ),
            resources=StepRunResponseResources(),
        )

    return f


@pytest.fixture
def create_pipeline_model(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> Callable[..., PipelineResponse]:
    """Fixture that returns a function which can be used to create a
    customizable PipelineResponseModel."""

    def f(
        **kwargs: Any,
    ) -> PipelineResponse:
        metadata_kwargs = dict(
            workspace=sample_workspace_model,
        )
        metadata_kwargs.update(kwargs)
        return PipelineResponse(
            id=uuid4(),
            name="sample_pipeline",
            body=PipelineResponseBody(
                created=datetime.now(),
                updated=datetime.now(),
                user=sample_user_model,
                tags=[],
            ),
            metadata=PipelineResponseMetadata(
                **metadata_kwargs,
            ),
        )

    return f


@pytest.fixture
def sample_deployment_response_model(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> PipelineDeploymentResponse:
    return PipelineDeploymentResponse(
        id=uuid4(),
        body=PipelineDeploymentResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_user_model,
        ),
        metadata=PipelineDeploymentResponseMetadata(
            workspace=sample_workspace_model,
            run_name_template="",
            pipeline_configuration={"name": ""},
            client_version="0.12.3",
            server_version="0.12.3",
        ),
    )


@pytest.fixture
def sample_build_response_model(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> PipelineBuildResponse:
    return PipelineBuildResponse(
        id=uuid4(),
        body=PipelineBuildResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_user_model,
        ),
        metadata=PipelineBuildResponseMetadata(
            workspace=sample_workspace_model,
            images={},
            is_local=False,
            contains_code=True,
        ),
    )


@pytest.fixture
def sample_code_repo_response_model(
    sample_user_model: UserResponse,
    sample_workspace_model: WorkspaceResponse,
) -> CodeRepositoryResponse:
    return CodeRepositoryResponse(
        id=uuid4(),
        name="name",
        body=CodeRepositoryResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_user_model,
            source={"module": "zenml", "type": "internal"},
        ),
        metadata=CodeRepositoryResponseMetadata(
            workspace=sample_workspace_model,
            config={},
        ),
    )


# Test data
service_id = "12345678-1234-5678-1234-567812345678"
service_name = "test_service"
service_type = ServiceType(
    type="model-serving", flavor="test_flavor", name="test_name"
)
service_source = "tests.unit.services.test_service.TestService"
admin_state = ServiceState.ACTIVE
config = {
    "type": "zenml.services.service.ServiceConfig",
    "name": "test_service",
    "description": "",
    "pipeline_name": "",
    "pipeline_step_name": "",
    "model_name": "",
    "model_version": "",
    "service_name": "zenml-test_service",
}
labels = {"label1": "value1", "label2": "value2"}
status = {
    "type": "zenml.services.service_status.ServiceStatus",
    "state": ServiceState.ACTIVE,
    "last_state": ServiceState.INACTIVE,
    "last_error": "",
}
endpoint = None
prediction_url = "http://example.com/predict"
health_check_url = "http://example.com/health"
created_time = datetime(2024, 3, 14, 10, 30)
updated_time = datetime(2024, 3, 14, 11, 45)


@pytest.fixture
def service_response(
    sample_user_model: UserResponse,
    sample_workspace_model,
):
    body = ServiceResponseBody(
        service_type=service_type,
        labels=labels,
        created=created_time,
        updated=updated_time,
        user=sample_user_model,
        state=admin_state,
    )
    metadata = ServiceResponseMetadata(
        service_source=service_source,
        admin_state=admin_state,
        config=config,
        status=status,
        endpoint=endpoint,
        prediction_url=prediction_url,
        health_check_url=health_check_url,
        workspace=sample_workspace_model,
    )
    return ServiceResponse(
        id=service_id,
        name=service_name,
        body=body,
        metadata=metadata,
    )
