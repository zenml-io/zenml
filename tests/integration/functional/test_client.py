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
import os
import random
import string
from contextlib import ExitStack as does_not_raise
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from uuid import uuid4

import pytest
from pydantic import BaseModel
from typing_extensions import Annotated

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from tests.integration.functional.utils import sample_name
from zenml import (
    ExternalArtifact,
    log_artifact_metadata,
    pipeline,
    save_artifact,
    step,
)
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source
from zenml.constants import PAGE_SIZE_DEFAULT
from zenml.enums import (
    MetadataResourceTypes,
    ModelStages,
    SecretScope,
    StackComponentType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    InitializationException,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.model.model import Model
from zenml.models import (
    ComponentResponse,
    ModelResponse,
    ModelVersionResponse,
    PipelineBuildRequest,
    PipelineDeploymentRequest,
    PipelineRequest,
    StackResponse,
)
from zenml.utils import io_utils
from zenml.utils.string_utils import random_str


def _create_local_orchestrator(
    client: Client,
    orchestrator_name: str = "OrchesTraitor",
) -> ComponentResponse:
    return client.create_stack_component(
        name=orchestrator_name,
        flavor="local",
        component_type=StackComponentType.ORCHESTRATOR,
        configuration={},
    )


def _create_local_artifact_store(
    client: Client,
    artifact_store_name: str = "Art-E-Fact",
) -> ComponentResponse:
    return client.create_stack_component(
        name=artifact_store_name,
        flavor="local",
        component_type=StackComponentType.ARTIFACT_STORE,
        configuration={},
    )


def _create_local_stack(
    client: Client,
    stack_name: str,
    orchestrator_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
) -> StackResponse:
    """Creates a local stack with components with the given names. If the names are not given, a random string is used instead."""

    def _random_name():
        return "".join(random.choices(string.ascii_letters, k=10))

    orchestrator = _create_local_orchestrator(
        client=client, orchestrator_name=orchestrator_name or _random_name()
    )

    artifact_store = _create_local_artifact_store(
        client=client,
        artifact_store_name=artifact_store_name or _random_name(),
    )

    return client.create_stack(
        name=stack_name,
        components={
            StackComponentType.ORCHESTRATOR: str(orchestrator.id),
            StackComponentType.ARTIFACT_STORE: str(artifact_store.id),
        },
    )


def test_repository_detection(tmp_path):
    """Tests detection of ZenML repositories in a directory."""
    assert Client.is_repository_directory(tmp_path) is False
    Client.initialize(tmp_path)
    assert Client.is_repository_directory(tmp_path) is True


def test_initializing_repo_creates_directory_and_uses_default_stack(
    tmp_path, clean_client
):
    """Tests that repo initialization creates a .zen directory and uses the default local stack."""
    Client.initialize(tmp_path)
    assert fileio.exists(str(tmp_path / ".zen"))

    client = Client()
    # switch to the new repo root
    client.activate_root(tmp_path)

    stack = client.active_stack_model
    assert isinstance(
        stack.components[StackComponentType.ORCHESTRATOR][0],
        ComponentResponse,
    )
    assert isinstance(
        stack.components[StackComponentType.ARTIFACT_STORE][0],
        ComponentResponse,
    )
    with pytest.raises(KeyError):
        assert stack.components[StackComponentType.CONTAINER_REGISTRY]


def test_initializing_repo_twice_fails(tmp_path):
    """Tests that initializing a repo in a directory where another repo already exists fails."""
    Client.initialize(tmp_path)
    with pytest.raises(InitializationException):
        Client.initialize(tmp_path)


def test_freshly_initialized_repo_attributes(tmp_path):
    """Tests that the attributes of a new repository are set correctly."""
    Client.initialize(tmp_path)
    client = Client(tmp_path)

    assert client.root == tmp_path


def test_finding_repository_directory_with_explicit_path(
    tmp_path, clean_client
):
    """Tests that a repository can be found using an explicit path, an environment variable and the current working directory."""
    subdirectory_path = tmp_path / "some_other_directory"
    io_utils.create_dir_recursive_if_not_exists(str(subdirectory_path))
    os.chdir(str(subdirectory_path))

    # no repo exists and explicit path passed
    assert Client.find_repository(tmp_path) is None
    assert Client(tmp_path).root is None

    # no repo exists and no path passed (=uses current working directory)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    # no repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]

    # initializing the repo
    Client.initialize(tmp_path)

    # repo exists and explicit path passed
    assert Client.find_repository(tmp_path) == tmp_path
    assert Client(tmp_path).root == tmp_path

    # repo exists and explicit path to subdirectory passed
    assert Client.find_repository(subdirectory_path) is None
    assert Client(subdirectory_path).root is None

    # repo exists and no path passed (=uses current working directory)
    assert Client.find_repository() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_repository() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path to subdirectory set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(subdirectory_path)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]


def test_creating_repository_instance_during_step_execution(mocker):
    """Tests that creating a Repository instance while a step is being executed does not fail."""
    mocker.patch(
        "zenml.environment.Environment.step_is_running",
        return_value=True,
    )
    with does_not_raise():
        Client()


def test_activating_nonexisting_stack_fails(clean_client):
    """Tests that activating a stack name that isn't registered fails."""
    with pytest.raises(KeyError):
        clean_client.activate_stack(str(uuid4()))


def test_activating_a_stack_updates_the_config_file(clean_client):
    """Tests that the newly active stack name gets persisted."""
    stack = _create_local_stack(client=clean_client, stack_name="new_stack")
    clean_client.activate_stack(stack.id)

    assert Client(clean_client.root).active_stack_model.name == stack.name


def test_registering_a_stack(clean_client):
    """Tests that registering a stack works and the stack gets persisted."""
    orch = _create_local_orchestrator(
        client=clean_client,
    )
    art = _create_local_artifact_store(
        client=clean_client,
    )
    new_stack_name = "some_new_stack_name"
    new_stack = clean_client.create_stack(
        name=new_stack_name,
        components={
            StackComponentType.ORCHESTRATOR: str(orch.id),
            StackComponentType.ARTIFACT_STORE: str(art.id),
        },
    )

    Client(clean_client.root)
    with does_not_raise():
        clean_client.zen_store.get_stack(new_stack.id)


def test_registering_a_stack_with_existing_name(clean_client):
    """Tests that registering a stack for an existing name fails."""
    _create_local_stack(
        client=clean_client,
        stack_name="axels_super_awesome_stack_of_fluffyness",
    )
    orchestrator = _create_local_orchestrator(clean_client)
    artifact_store = _create_local_artifact_store(clean_client)

    with pytest.raises(StackExistsError):
        clean_client.create_stack(
            name="axels_super_awesome_stack_of_fluffyness",
            components={
                StackComponentType.ORCHESTRATOR: str(orchestrator.id),
                StackComponentType.ARTIFACT_STORE: str(artifact_store.id),
            },
        )


def test_updating_a_stack_with_new_component_succeeds(clean_client):
    """Tests that updating a new stack with already registered components updates the stack with the new or altered components passed in."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )
    clean_client.activate_stack(stack_name_id_or_prefix=stack.name)

    old_orchestrator = stack.components[StackComponentType.ORCHESTRATOR][0]
    old_artifact_store = stack.components[StackComponentType.ARTIFACT_STORE][0]
    orchestrator = _create_local_orchestrator(
        client=clean_client, orchestrator_name="different_orchestrator"
    )

    with does_not_raise():
        updated_stack = clean_client.update_stack(
            name_id_or_prefix=stack.name,
            component_updates={
                StackComponentType.ORCHESTRATOR: [str(orchestrator.id)],
            },
        )

    active_orchestrator = updated_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0]
    active_artifact_store = updated_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0]
    assert active_orchestrator != old_orchestrator
    assert active_orchestrator == orchestrator
    assert active_artifact_store == old_artifact_store


def test_renaming_stack_with_update_method_succeeds(clean_client):
    """Tests that renaming a stack with the update method succeeds."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )
    clean_client.activate_stack(stack.id)

    new_stack_name = "new_stack_name"

    with does_not_raise():
        clean_client.update_stack(
            name_id_or_prefix=stack.id, name=new_stack_name
        )
    assert clean_client.get_stack(name_id_or_prefix=new_stack_name)


def test_register_a_stack_with_unregistered_component_fails(clean_client):
    """Tests that registering a stack with an unregistered component fails."""
    with pytest.raises(KeyError):
        clean_client.create_stack(
            name="axels_empty_stack_of_disappoint",
            components={
                StackComponentType.ORCHESTRATOR: "orchestrator_doesnt_exist",
                StackComponentType.ARTIFACT_STORE: "this_also_doesnt",
            },
        )


def test_deregistering_the_active_stack(clean_client):
    """Tests that deregistering the active stack fails."""
    with pytest.raises(ValueError):
        clean_client.delete_stack(clean_client.active_stack_model.id)


def test_deregistering_a_non_active_stack(clean_client):
    """Tests that deregistering a non-active stack works."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )

    with does_not_raise():
        clean_client.delete_stack(name_id_or_prefix=stack.id)


def test_getting_a_stack_component(clean_client):
    """Tests that getting a stack component returns the correct component."""
    component = clean_client.active_stack_model.components[
        StackComponentType.ORCHESTRATOR
    ][0]
    with does_not_raise():
        registered_component = clean_client.get_stack_component(
            component_type=component.type, name_id_or_prefix=component.id
        )

    assert component == registered_component


def test_getting_a_nonexisting_stack_component(clean_client):
    """Tests that getting a stack component for a name that isn't registered fails."""
    with pytest.raises(KeyError):
        clean_client.get_stack(name_id_or_prefix=str(uuid4()))


def test_registering_a_stack_component_with_existing_name(clean_client):
    """Tests that registering a stack component for an existing name fails."""
    _create_local_orchestrator(
        client=clean_client, orchestrator_name="axels_orchestration_laboratory"
    )
    with pytest.raises(StackComponentExistsError):
        clean_client.create_stack_component(
            name="axels_orchestration_laboratory",
            flavor="local",
            component_type=StackComponentType.ORCHESTRATOR,
            configuration={},
        )


def test_registering_a_new_stack_component_succeeds(clean_client):
    """Tests that registering a stack component works and is persisted."""
    new_artifact_store = _create_local_artifact_store(client=clean_client)

    new_client = Client(clean_client.root)

    with does_not_raise():
        registered_artifact_store = new_client.get_stack_component(
            component_type=new_artifact_store.type,
            name_id_or_prefix=new_artifact_store.id,
        )

    assert registered_artifact_store == new_artifact_store


def test_deregistering_a_stack_component_in_stack_fails(clean_client):
    """Tests that deregistering a stack component works and is persisted."""
    component = _create_local_stack(
        clean_client,
        "local_stack",
        orchestrator_name="unregistered_orchestrator",
    ).components[StackComponentType.ORCHESTRATOR][0]

    with pytest.raises(IllegalOperationError):
        clean_client.delete_stack_component(
            component_type=StackComponentType.ORCHESTRATOR,
            name_id_or_prefix=str(component.id),
        )


def test_deregistering_a_stack_component_that_is_part_of_a_registered_stack(
    clean_client,
):
    """Tests that deregistering a stack component that is part of a registered stack fails."""
    component = clean_client.active_stack_model.components[
        StackComponentType.ORCHESTRATOR
    ][0]

    with pytest.raises(IllegalOperationError):
        clean_client.delete_stack_component(
            name_id_or_prefix=component.id,
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_getting_a_pipeline(clean_client: "Client"):
    """Tests fetching of a pipeline."""
    # Non-existent ID
    with pytest.raises(KeyError):
        clean_client.get_pipeline(name_id_or_prefix=uuid4())

    # Non-existent name
    with pytest.raises(KeyError):
        clean_client.get_pipeline(name_id_or_prefix="non_existent")

    request = PipelineRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        name="pipeline",
        version="1",
        version_hash="",
        spec=PipelineSpec(steps=[]),
    )
    response_1 = clean_client.zen_store.create_pipeline(request)

    pipeline = clean_client.get_pipeline(name_id_or_prefix=response_1.id)
    assert pipeline == response_1

    pipeline = clean_client.get_pipeline(name_id_or_prefix="pipeline")
    assert pipeline == response_1

    pipeline = clean_client.get_pipeline(
        name_id_or_prefix="pipeline", version="1"
    )
    assert pipeline == response_1

    # Non-existent version
    with pytest.raises(KeyError):
        clean_client.get_pipeline(name_id_or_prefix="pipeline", version="2")

    request.version = "2"
    request.version_hash = "foo"
    response_2 = clean_client.zen_store.create_pipeline(request)

    # Gets latest version
    pipeline = clean_client.get_pipeline(name_id_or_prefix="pipeline")
    assert pipeline == response_2


def test_listing_pipelines(clean_client):
    """Tests listing of pipelines."""
    assert clean_client.list_pipelines().total == 0

    request = PipelineRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        name="pipeline",
        version="1",
        version_hash="",
        spec=PipelineSpec(steps=[]),
    )
    response_1 = clean_client.zen_store.create_pipeline(request)
    request.name = "other_pipeline"
    request.version = "2"
    response_2 = clean_client.zen_store.create_pipeline(request)

    assert clean_client.list_pipelines().total == 2

    assert clean_client.list_pipelines(name="pipeline").total == 1
    assert clean_client.list_pipelines(name="pipeline").items[0] == response_1

    assert clean_client.list_pipelines(version="1").total == 1
    assert clean_client.list_pipelines(version="1").items[0] == response_1

    assert clean_client.list_pipelines(version="2").total == 1
    assert clean_client.list_pipelines(version="2").items[0] == response_2

    assert (
        clean_client.list_pipelines(name="other_pipeline", version="3").total
        == 0
    )


def test_create_run_metadata_for_pipeline_run(clean_client_with_run: Client):
    """Test creating run metadata linked only to a pipeline run."""
    pipeline_run = clean_client_with_run.list_runs()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"},
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )
    assert isinstance(new_metadata, list)
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].resource_id == pipeline_run.id
    assert new_metadata[0].resource_type == MetadataResourceTypes.PIPELINE_RUN
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the pipeline run
    all_metadata = clean_client_with_run.list_run_metadata(
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )
    assert len(all_metadata) == len(existing_metadata) + 1


def test_create_run_metadata_for_pipeline_run_and_component(
    clean_client_with_run: Client,
):
    """Test creating metadata linked to a pipeline run and a stack component"""
    pipeline_run = clean_client_with_run.list_runs()[0]
    orchestrator_id = clean_client_with_run.active_stack_model.components[
        "orchestrator"
    ][0].id
    existing_metadata = clean_client_with_run.list_run_metadata(
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )
    existing_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"aria": "is awesome too"},
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
        stack_component_id=orchestrator_id,
    )
    assert isinstance(new_metadata, list)
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "aria"
    assert new_metadata[0].value == "is awesome too"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].resource_id == pipeline_run.id
    assert new_metadata[0].resource_type == MetadataResourceTypes.PIPELINE_RUN
    assert new_metadata[0].stack_component_id == orchestrator_id

    # Assert new metadata is linked to the pipeline run
    registered_metadata = clean_client_with_run.list_run_metadata(
        resource_id=pipeline_run.id,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )
    assert len(registered_metadata) == len(existing_metadata) + 1

    # Assert new metadata is linked to the stack component
    registered_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )
    assert (
        len(registered_component_metadata)
        == len(existing_component_metadata) + 1
    )


def test_create_run_metadata_for_step_run(clean_client_with_run: Client):
    """Test creating run metadata linked only to a step run."""
    step_run = clean_client_with_run.list_run_steps()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        resource_id=step_run.id, resource_type=MetadataResourceTypes.STEP_RUN
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"},
        resource_id=step_run.id,
        resource_type=MetadataResourceTypes.STEP_RUN,
    )
    assert isinstance(new_metadata, list)
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].resource_id == step_run.id
    assert new_metadata[0].resource_type == MetadataResourceTypes.STEP_RUN
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the step run
    registered_metadata = clean_client_with_run.list_run_metadata(
        resource_id=step_run.id, resource_type=MetadataResourceTypes.STEP_RUN
    )
    assert len(registered_metadata) == len(existing_metadata) + 1


def test_create_run_metadata_for_step_run_and_component(
    clean_client_with_run: Client,
):
    """Test creating metadata linked to a step run and a stack component"""
    step_run = clean_client_with_run.list_run_steps()[0]
    orchestrator_id = clean_client_with_run.active_stack_model.components[
        "orchestrator"
    ][0].id
    existing_metadata = clean_client_with_run.list_run_metadata(
        resource_id=step_run.id, resource_type=MetadataResourceTypes.STEP_RUN
    )
    existing_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"aria": "is awesome too"},
        resource_id=step_run.id,
        resource_type=MetadataResourceTypes.STEP_RUN,
        stack_component_id=orchestrator_id,
    )
    assert isinstance(new_metadata, list)
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "aria"
    assert new_metadata[0].value == "is awesome too"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].resource_id == step_run.id
    assert new_metadata[0].resource_type == MetadataResourceTypes.STEP_RUN
    assert new_metadata[0].stack_component_id == orchestrator_id

    # Assert new metadata is linked to the step run
    registered_metadata = clean_client_with_run.list_run_metadata(
        resource_id=step_run.id, resource_type=MetadataResourceTypes.STEP_RUN
    )
    assert len(registered_metadata) == len(existing_metadata) + 1

    # Assert new metadata is linked to the stack component
    registered_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )
    assert (
        len(registered_component_metadata)
        == len(existing_component_metadata) + 1
    )


def test_create_run_metadata_for_artifact(clean_client_with_run: Client):
    """Test creating run metadata linked to an artifact."""
    artifact_version = clean_client_with_run.list_artifact_versions()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        resource_id=artifact_version.id,
        resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"},
        resource_id=artifact_version.id,
        resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
    )
    assert isinstance(new_metadata, list)
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].resource_id == artifact_version.id
    assert (
        new_metadata[0].resource_type == MetadataResourceTypes.ARTIFACT_VERSION
    )
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the artifact
    registered_metadata = clean_client_with_run.list_run_metadata(
        resource_id=artifact_version.id,
        resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
    )
    assert len(registered_metadata) == len(existing_metadata) + 1


# .---------.
# | SECRETS |
# '---------'


def random_secret_name(prefix: str = "aria") -> str:
    """Function to get a random secret name or prefix."""
    return f"pytest_{prefix}_{random_str(4)}"


@contextmanager
def random_secret_context() -> Generator[str, None, None]:
    """Context for testing secrets.

    Generates a random secret prefix to avoid conflicts. Yields the prefix.
    After the context is exited, all secrets with that prefix are deleted.
    """
    prefix = random_secret_name()
    yield prefix

    client = Client()
    for secret in client.list_secrets(name=f"startswith:{prefix}").items:
        client.delete_secret(secret.id)


def test_create_secret_default_scope():
    """Test that secrets are created in the workspace scope by default."""
    client = Client()
    with random_secret_context() as name:
        s = client.create_secret(
            name=name,
            values={"key": "value"},
        )
        assert s.scope == SecretScope.WORKSPACE
        assert s.name == name
        assert s.secret_values == {"key": "value"}


def test_create_secret_user_scope():
    """Test creating secrets in the user scope."""
    client = Client()
    with random_secret_context() as name:
        s = client.create_secret(
            name=name,
            scope=SecretScope.USER,
            values={"key": "value"},
        )
        assert s.scope == SecretScope.USER
        assert s.name == name
        assert s.secret_values == {"key": "value"}


def test_create_secret_existing_name_scope():
    """Test that creating a secret with an existing name fails."""
    client = Client()
    with random_secret_context() as name:
        client.create_secret(
            name=name,
            values={"key": "value"},
        )

        with pytest.raises(EntityExistsError):
            client.create_secret(
                name=name,
                values={"key": "value"},
            )


def test_create_secret_existing_name_user_scope():
    """Test that creating a secret with an existing name in the user scope fails."""
    client = Client()
    with random_secret_context() as name:
        client.create_secret(
            name=name,
            scope=SecretScope.USER,
            values={"key": "value"},
        )

        with pytest.raises(EntityExistsError):
            client.create_secret(
                name=name,
                scope=SecretScope.USER,
                values={"key": "value"},
            )


def test_create_secret_existing_name_different_scope():
    """Test that creating a secret with the same name in different scopes succeeds."""
    client = Client()
    with random_secret_context() as name:
        s1 = client.create_secret(
            name=name,
            values={"key": "value"},
        )

        with does_not_raise():
            s2 = client.create_secret(
                name=name,
                scope=SecretScope.USER,
                values={"key": "value"},
            )

        assert s1.id != s2.id
        assert s1.name == s2.name


# ---------------
# Pipeline Builds
# ---------------


def test_listing_builds(clean_client):
    """Tests listing builds."""
    builds = clean_client.list_builds()
    assert len(builds) == 0

    request = PipelineBuildRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        images={},
        is_local=False,
        contains_code=True,
    )
    response = clean_client.zen_store.create_build(request)

    builds = clean_client.list_builds()
    assert len(builds) == 1
    assert builds[0] == response

    builds = clean_client.list_builds(stack_id=uuid4())
    assert len(builds) == 0


def test_getting_builds(clean_client):
    """Tests getting builds."""

    with pytest.raises(KeyError):
        clean_client.get_build(str(uuid4()))

    request = PipelineBuildRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        images={},
        is_local=False,
        contains_code=True,
    )
    response = clean_client.zen_store.create_build(request)

    with does_not_raise():
        build = clean_client.get_build(str(response.id))

    assert build == response


def test_deleting_builds(clean_client):
    """Tests deleting builds."""
    with pytest.raises(KeyError):
        clean_client.delete_build(str(uuid4()))

    request = PipelineBuildRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        images={},
        is_local=False,
        contains_code=True,
    )
    response = clean_client.zen_store.create_build(request)

    with does_not_raise():
        clean_client.delete_build(str(response.id))

    with pytest.raises(KeyError):
        clean_client.get_build(str(response.id))


# --------------------
# Pipeline Deployments
# --------------------


def test_listing_deployments(clean_client):
    """Tests listing deployments."""
    deployments = clean_client.list_deployments()
    assert len(deployments) == 0

    request = PipelineDeploymentRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        stack=clean_client.active_stack.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline_name"},
        client_version="0.12.3",
        server_version="0.12.3",
    )
    response = clean_client.zen_store.create_deployment(request)

    deployments = clean_client.list_deployments()
    assert len(deployments) == 1
    assert deployments[0] == response

    deployments = clean_client.list_deployments(stack_id=uuid4())
    assert len(deployments) == 0


def test_getting_deployments(clean_client):
    """Tests getting deployments."""
    with pytest.raises(KeyError):
        clean_client.get_deployment(str(uuid4()))

    request = PipelineDeploymentRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        stack=clean_client.active_stack.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline_name"},
        client_version="0.12.3",
        server_version="0.12.3",
    )
    response = clean_client.zen_store.create_deployment(request)

    with does_not_raise():
        deployment = clean_client.get_deployment(str(response.id))

    assert deployment == response


def test_deleting_deployments(clean_client):
    """Tests deleting deployments."""
    with pytest.raises(KeyError):
        clean_client.delete_deployment(str(uuid4()))

    request = PipelineDeploymentRequest(
        user=clean_client.active_user.id,
        workspace=clean_client.active_workspace.id,
        stack=clean_client.active_stack.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline_name"},
        client_version="0.12.3",
        server_version="0.12.3",
    )
    response = clean_client.zen_store.create_deployment(request)

    with does_not_raise():
        clean_client.delete_deployment(str(response.id))

    with pytest.raises(KeyError):
        clean_client.get_deployment(str(response.id))


def test_get_run(clean_client: Client, connected_two_step_pipeline):
    """Test that `get_run()` returns the correct run."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    run_ = clean_client.get_pipeline("connected_two_step_pipeline").runs[0]
    assert clean_client.get_pipeline_run(run_.name) == run_


def test_get_run_fails_for_non_existent_run(clean_client: Client):
    """Test that `get_run()` raises a `KeyError` for non-existent runs."""
    with pytest.raises(KeyError):
        clean_client.get_pipeline_run("non_existent_run")


def test_get_unlisted_runs(clean_client: Client, connected_two_step_pipeline):
    """Test that listing unlisted runs works."""
    assert len(clean_client.list_pipeline_runs(unlisted=True)) == 0
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    assert len(clean_client.list_pipeline_runs(unlisted=True)) == 0
    pipeline_instance.run(unlisted=True)
    assert len(clean_client.list_pipeline_runs(unlisted=True)) == 1


class ClientCrudTestConfig(BaseModel):
    entity_name: str
    create_args: Dict[str, Any] = {}
    get_args: Dict[str, Any] = {}
    update_args: Dict[str, Any] = {}
    delete_args: Dict[str, Any] = {}


crud_test_configs = [
    ClientCrudTestConfig(
        entity_name="user",
        create_args={"name": sample_name("user_name")},
        update_args={"updated_name": sample_name("updated_user_name")},
    ),
    ClientCrudTestConfig(
        entity_name="workspace",
        create_args={"name": sample_name("workspace_name"), "description": ""},
        update_args={"new_name": sample_name("updated_workspace_name")},
    ),
    ClientCrudTestConfig(
        entity_name="stack",
        create_args={
            "name": sample_name("stack_name"),
            "components": {
                StackComponentType.ORCHESTRATOR: "default",
                StackComponentType.ARTIFACT_STORE: "default",
            },
        },
        update_args={"name": sample_name("updated_stack_name")},
    ),
    ClientCrudTestConfig(
        entity_name="stack_component",
        create_args={
            "name": sample_name("stack_component_name"),
            "flavor": "local",
            "component_type": StackComponentType.ORCHESTRATOR,
            "configuration": {},
        },
        get_args={"component_type": StackComponentType.ORCHESTRATOR},
        update_args={
            "name": sample_name("updated_stack_component_name"),
            "component_type": StackComponentType.ORCHESTRATOR,
        },
        delete_args={"component_type": StackComponentType.ORCHESTRATOR},
    ),
    ClientCrudTestConfig(
        entity_name="flavor",
        create_args={
            "source": "tests.unit.test_flavor.AriaOrchestratorFlavor",
            "component_type": StackComponentType.ORCHESTRATOR,
        },
    ),
    ClientCrudTestConfig(
        entity_name="code_repository",
        create_args={
            "name": sample_name("code_repository_name"),
            "config": {},
            "source": Source(
                module="tests.unit.pipelines.test_build_utils",
                attribute="StubCodeRepository",
                type="unknown",
            ),
        },
        update_args={
            "name": sample_name("updated_code_repository_name"),
        },
    ),
]


@pytest.mark.parametrize(
    "crud_test_config",
    crud_test_configs,
    ids=[c.entity_name for c in crud_test_configs],
)
def test_basic_crud_for_entity(
    crud_test_config: ClientCrudTestConfig, clean_client
):
    """Tests basic CRUD method on the client."""
    create_method = getattr(
        clean_client, f"create_{crud_test_config.entity_name}"
    )
    get_method = getattr(clean_client, f"get_{crud_test_config.entity_name}")
    delete_method = getattr(
        clean_client, f"delete_{crud_test_config.entity_name}"
    )

    entity = create_method(**crud_test_config.create_args)
    try:
        assert hasattr(entity, "name")
        assert len(getattr(entity, "name")) > 1

        with does_not_raise():
            get_method(
                name_id_or_prefix=entity.name, **crud_test_config.get_args
            )
            get_method(
                name_id_or_prefix=entity.id, **crud_test_config.get_args
            )
            get_method(
                name_id_or_prefix=entity.name[:-1],
                allow_name_prefix_match=True,
                **crud_test_config.get_args,
            )

        with pytest.raises(KeyError):
            get_method(
                name_id_or_prefix=entity.name[:-1],
                allow_name_prefix_match=False,
                **crud_test_config.get_args,
            )

        if hasattr(clean_client, f"update_{crud_test_config.entity_name}"):
            update_method = getattr(
                clean_client, f"update_{crud_test_config.entity_name}"
            )

            # Updating works with id prefix
            id_prefix = str(entity.id)[:5]
            entity = update_method(
                name_id_or_prefix=id_prefix, **crud_test_config.update_args
            )

            with pytest.raises(KeyError):
                # Updating doesn't work with name prefix
                update_method(
                    name_id_or_prefix=entity.name[:-1],
                    **crud_test_config.update_args,
                )

        with pytest.raises(KeyError):
            # Deleting doesn't work with name prefix
            delete_method(
                name_id_or_prefix=entity.name[:-1],
                **crud_test_config.delete_args,
            )

        # Deleting works with id prefix
        id_prefix = str(entity.id)[:5]
        delete_method(
            name_id_or_prefix=id_prefix, **crud_test_config.delete_args
        )
    finally:
        # Make sure to delete the created entity to not leave anything in the
        # workspace.
        try:
            delete_method(entity.id, **crud_test_config.delete_args)
        except KeyError:
            # This means the test already succeeded and deleted the entity,
            # nothing to do here
            pass


@step
def lazy_producer_test_artifact() -> Annotated[str, "new_one"]:
    """Produce artifact with metadata."""
    from zenml.client import Client

    log_artifact_metadata(metadata={"some_meta": "meta_new_one"})

    client = Client()
    model = client.create_model(name="model_name", description="model_desc")
    client.create_model_version(
        model_name_or_id=model.id,
        name="model_version",
        description="mv_desc_1",
    )
    mv = client.create_model_version(
        model_name_or_id=model.id,
        name="model_version2",
        description="mv_desc_2",
    )
    client.update_model_version(
        model_name_or_id=model.id, version_name_or_id=mv.id, stage="staging"
    )
    return "body_new_one"


@step
def lazy_asserter_test_artifact(
    artifact_existing: str,
    artifact_metadata_existing: str,
    artifact_new: str,
    artifact_metadata_new: str,
    model: ModelResponse,
    model_version_by_version: ModelVersionResponse,
    model_version_by_stage: ModelVersionResponse,
):
    """Assert that passed in values are loaded in lazy mode.
    They do not exists before actual run of the pipeline.
    """
    assert artifact_existing == "body_preexisting"
    assert artifact_metadata_existing == "meta_preexisting"
    assert artifact_new == "body_new_one"
    assert artifact_metadata_new == "meta_new_one"

    assert model.name == "model_name"
    assert model.description == "model_desc"
    assert model_version_by_version.name == "model_version"
    assert model_version_by_version.description == "mv_desc_1"
    assert model_version_by_stage.name == "model_version2"
    assert model_version_by_stage.description == "mv_desc_2"


class TestArtifact:
    def test_prune_full(self, clean_client: "Client"):
        """Test that artifact pruning works."""
        artifact_id = ExternalArtifact(value="foo").upload_by_value()
        artifact = clean_client.get_artifact_version(artifact_id)
        assert artifact is not None
        clean_client.prune_artifacts(
            only_versions=False, delete_from_artifact_store=True
        )
        # artifact version, artifact and data are deleted
        with pytest.raises(KeyError):
            clean_client.get_artifact_version(artifact_id)
        with pytest.raises(KeyError):
            assert (
                clean_client.get_artifact(artifact.artifact.id).id
                == artifact.artifact.id
            )
        assert not os.path.exists(artifact.uri)

    def test_prune_data_and_version(self, clean_client: "Client"):
        """Test that artifact pruning works with delete_from_artifact_store flag."""
        artifact_id = ExternalArtifact(value="foo").upload_by_value()
        artifact = clean_client.get_artifact_version(artifact_id)
        assert artifact is not None
        clean_client.prune_artifacts(
            only_versions=False, delete_from_artifact_store=False
        )
        # artifact version and artifact are deleted, data is kept
        with pytest.raises(KeyError):
            clean_client.get_artifact_version(artifact_id)
        with pytest.raises(KeyError):
            assert (
                clean_client.get_artifact(artifact.artifact.id).id
                == artifact.artifact.id
            )
        assert os.path.exists(artifact.uri)

    def test_prune_only_artifact_version(self, clean_client: "Client"):
        """Test that artifact pruning works with only versions flag."""
        artifact_id = ExternalArtifact(value="foo").upload_by_value()
        artifact = clean_client.get_artifact_version(artifact_id)
        assert artifact is not None
        clean_client.prune_artifacts(only_versions=True)
        # artifact version is deleted, rest kept
        with pytest.raises(KeyError):
            clean_client.get_artifact_version(artifact_id)
        assert (
            clean_client.get_artifact(artifact.artifact.id).id
            == artifact.artifact.id
        )
        assert os.path.exists(artifact.uri)

    def test_pipeline_can_load_in_lazy_mode(
        self,
        clean_client: "Client",
    ):
        """Tests that user can load model artifact versions, metadata and models (versions) in lazy mode in pipeline codes."""

        @pipeline(enable_cache=False)
        def dummy():
            artifact_existing = clean_client.get_artifact_version(
                name_id_or_prefix="preexisting"
            )
            artifact_metadata_existing = artifact_existing.run_metadata[
                "some_meta"
            ]

            artifact_new = clean_client.get_artifact_version(
                name_id_or_prefix="new_one"
            )
            artifact_metadata_new = artifact_new.run_metadata["some_meta"]

            model = clean_client.get_model(model_name_or_id="model_name")

            lazy_producer_test_artifact()
            lazy_asserter_test_artifact(
                # load artifact directly
                artifact_existing.load(),
                # pass as run metadata response
                artifact_metadata_existing,
                # pass as artifact response
                artifact_new,
                # read value of metadata directly
                artifact_metadata_new.value,
                # load model
                model,
                # load model version by version
                clean_client.get_model_version(
                    # this can be lazy loaders too
                    model_name_or_id=model.id,
                    model_version_name_or_number_or_id="model_version",
                ),
                # load model version by stage
                clean_client.get_model_version(
                    # this can be lazy loaders too
                    model.id,
                    model_version_name_or_number_or_id="staging",
                ),
                after=["lazy_producer_test_artifact"],
            )

        save_artifact(
            data="body_preexisting", name="preexisting", version="1.2.3"
        )
        log_artifact_metadata(
            metadata={"some_meta": "meta_preexisting"},
            artifact_name="preexisting",
            artifact_version="1.2.3",
        )
        with pytest.raises(KeyError):
            clean_client.get_artifact_version("new_one")
        dummy()


class TestModel:
    MODEL_NAME = "foo"

    @staticmethod
    @pytest.fixture
    def client_with_model(clean_client: "Client") -> "Client":
        clean_client.create_model(
            name=TestModel.MODEL_NAME,
            license="l",
            description="d",
            audience="a",
            use_cases="u",
            limitations="l",
            trade_offs="t",
            ethics="e",
            tags=["t", "t2"],
        )
        return clean_client

    def test_get_model_found(self, client_with_model: "Client"):
        model = client_with_model.get_model(self.MODEL_NAME)

        assert model.name == self.MODEL_NAME
        assert model.license == "l"
        assert model.description == "d"
        assert model.audience == "a"
        assert model.use_cases == "u"
        assert model.limitations == "l"
        assert model.trade_offs == "t"
        assert model.ethics == "e"
        assert {t.name for t in model.tags} == {"t", "t2"}

    def test_get_model_not_found(self, clean_client: "Client"):
        with pytest.raises(KeyError):
            clean_client.get_model(self.MODEL_NAME)

    def test_create_model_pass(self, clean_client: "Client"):
        clean_client.create_model(name="some")
        model = clean_client.get_model("some")

        assert model.name == "some"

        clean_client.create_model(
            name=self.MODEL_NAME,
            license="l",
            description="d",
            audience="a",
            use_cases="u",
            limitations="l",
            trade_offs="t",
            ethics="e",
            tags=["t", "t2"],
        )
        model = clean_client.get_model(self.MODEL_NAME)

        assert model.name == self.MODEL_NAME
        assert model.license == "l"
        assert model.description == "d"
        assert model.audience == "a"
        assert model.use_cases == "u"
        assert model.limitations == "l"
        assert model.trade_offs == "t"
        assert model.ethics == "e"
        assert {t.name for t in model.tags} == {"t", "t2"}

    def test_create_model_duplicate_fail(self, client_with_model: "Client"):
        with pytest.raises(EntityExistsError):
            client_with_model.create_model(self.MODEL_NAME)

    def test_delete_model_found(self, client_with_model: "Client"):
        client_with_model.delete_model(self.MODEL_NAME)

        with pytest.raises(KeyError):
            client_with_model.get_model(self.MODEL_NAME)

    def test_delete_model_not_found(self, clean_client: "Client"):
        with pytest.raises(KeyError):
            clean_client.delete_model(self.MODEL_NAME)

    def test_update_model(self, client_with_model: "Client"):
        client_with_model.update_model(
            self.MODEL_NAME, add_tags=["t3"], remove_tags=["t2"]
        )
        model = client_with_model.get_model(self.MODEL_NAME)

        assert model.name == self.MODEL_NAME
        assert model.license == "l"
        assert model.description == "d"
        assert model.audience == "a"
        assert model.use_cases == "u"
        assert model.limitations == "l"
        assert model.trade_offs == "t"
        assert model.ethics == "e"
        assert {t.name for t in model.tags} == {"t", "t3"}

        client_with_model.update_model(
            self.MODEL_NAME,
            license="L",
            description="D",
            audience="A",
            use_cases="U",
            limitations="L",
            trade_offs="T",
            ethics="E",
        )
        model = client_with_model.get_model(self.MODEL_NAME)

        assert model.name == self.MODEL_NAME
        assert model.license == "L"
        assert model.description == "D"
        assert model.audience == "A"
        assert model.use_cases == "U"
        assert model.limitations == "L"
        assert model.trade_offs == "T"
        assert model.ethics == "E"
        assert {t.name for t in model.tags} == {"t", "t3"}

    def test_name_is_mutable(self, clean_client: "Client"):
        """Test that model version name is mutable."""
        model = clean_client.create_model(name=self.MODEL_NAME)

        model = clean_client.get_model(model.id)
        assert model.name == self.MODEL_NAME

        clean_client.update_model(model.id, name="bar")
        model = clean_client.get_model(model.id)
        assert model.name == "bar"

    def test_latest_version_retrieval(self, clean_client: "Client"):
        """Test that model response has proper latest version in it."""
        model = clean_client.create_model(name=self.MODEL_NAME)
        mv1 = clean_client.create_model_version(model.id, name="foo")
        model_ = clean_client.get_model(model.id)
        assert model_.latest_version_name == mv1.name
        assert model_.latest_version_id == mv1.id

        mv2 = clean_client.create_model_version(model.id, name="bar")
        model_ = clean_client.get_model(model.id)
        assert model_.latest_version_name == mv2.name
        assert model_.latest_version_id == mv2.id

    def test_list_by_tags(self, clean_client: "Client"):
        """Test that models can be listed using tag filters."""
        model1 = clean_client.create_model(
            name=self.MODEL_NAME, tags=["foo", "bar"]
        )
        model2 = clean_client.create_model(
            name=self.MODEL_NAME + "2", tags=["foo"]
        )
        ms = clean_client.list_models(tag="foo")
        assert len(ms) == 2
        assert model1 in ms
        assert model2 in ms

        ms = clean_client.list_models(tag="bar")
        assert len(ms) == 1
        assert model1 in ms

        ms = clean_client.list_models(tag="non_existent_tag")
        assert len(ms) == 0

        ms = clean_client.list_models()
        assert len(ms) == 2
        assert model1 in ms
        assert model2 in ms

        ms = clean_client.list_models(tag="")
        assert len(ms) == 2
        assert model1 in ms
        assert model2 in ms


class TestModelVersion:
    MODEL_NAME = "foo"
    VERSION_NAME = "bar"
    VERSION_DESC = "version desc"

    @staticmethod
    @pytest.fixture
    def client_with_model(clean_client: "Client"):
        clean_client.create_model(name=TestModelVersion.MODEL_NAME)
        clean_client.create_model_version(
            model_name_or_id=TestModelVersion.MODEL_NAME,
            name=TestModelVersion.VERSION_NAME,
            description=TestModelVersion.VERSION_DESC,
        )
        return clean_client

    def test_get_model_version_by_name_found(
        self, client_with_model: "Client"
    ):
        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, self.VERSION_NAME
        )

        assert model_version.model.name == self.MODEL_NAME
        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC

    def test_get_model_version_by_id_found(self, client_with_model: "Client"):
        mv = client_with_model.get_model_version(
            self.MODEL_NAME, self.VERSION_NAME
        )

        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, mv.id
        )

        assert model_version.model.name == self.MODEL_NAME
        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC

    def test_get_model_version_by_index_found(
        self, client_with_model: "Client"
    ):
        model_version = client_with_model.get_model_version(self.MODEL_NAME, 1)

        assert model_version.model.name == self.MODEL_NAME
        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC

    def test_get_model_version_by_stage_found(
        self, client_with_model: "Client"
    ):
        client_with_model.update_model_version(
            model_name_or_id=self.MODEL_NAME,
            version_name_or_id=self.VERSION_NAME,
            stage=ModelStages.STAGING,
            force=True,
        )

        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, ModelStages.STAGING
        )

        assert model_version.model.name == self.MODEL_NAME
        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC

    def test_get_model_version_by_stage_not_found(
        self, client_with_model: "Client"
    ):
        with pytest.raises(KeyError):
            client_with_model.get_model_version(
                self.MODEL_NAME, ModelStages.STAGING
            )

    def test_get_model_version_not_found(self, client_with_model: "Client"):
        with pytest.raises(KeyError):
            client_with_model.get_model_version(self.MODEL_NAME, 42)

    def test_create_model_version_pass(self, client_with_model: "Client"):
        model_version = client_with_model.create_model_version(self.MODEL_NAME)

        assert model_version.name == "2"
        assert model_version.number == 2
        assert model_version.description is None

        model_version = client_with_model.create_model_version(
            self.MODEL_NAME, "new version"
        )

        assert model_version.name == "new version"
        assert model_version.number == 3
        assert model_version.description is None

        model_version = client_with_model.create_model_version(
            self.MODEL_NAME, description="some desc"
        )

        assert model_version.name == "4"
        assert model_version.number == 4
        assert model_version.description == "some desc"

        model_version = client_with_model.create_model_version(
            self.MODEL_NAME, tags=["a", "b"]
        )

        assert model_version.name == "5"
        assert model_version.number == 5
        assert {t.name for t in model_version.tags} == {"a", "b"}

    def test_create_model_version_duplicate_fails(
        self, client_with_model: "Client"
    ):
        with pytest.raises(EntityExistsError):
            client_with_model.create_model_version(
                self.MODEL_NAME, self.VERSION_NAME
            )

    def test_update_model_version(self, client_with_model: "Client"):
        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, self.VERSION_NAME
        )

        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC
        assert model_version.stage is None

        client_with_model.update_model_version(
            self.MODEL_NAME, self.VERSION_NAME, stage="staging"
        )
        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, self.VERSION_NAME
        )

        assert model_version.name == self.VERSION_NAME
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC
        assert model_version.stage == ModelStages.STAGING

        client_with_model.update_model_version(
            self.MODEL_NAME, self.VERSION_NAME, name="new name"
        )
        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, "new name"
        )

        assert model_version.name == "new name"
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC
        assert model_version.stage == ModelStages.STAGING

        client_with_model.create_model_version(
            self.MODEL_NAME, "other version"
        )
        with pytest.raises(RuntimeError):
            client_with_model.update_model_version(
                self.MODEL_NAME,
                "other version",
                stage=ModelStages.STAGING,
                force=False,
            )

        client_with_model.update_model_version(
            self.MODEL_NAME,
            "other version",
            stage=ModelStages.STAGING,
            force=True,
        )
        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, "other version"
        )

        assert model_version.name == "other version"
        assert model_version.number == 2
        assert model_version.description is None
        assert model_version.stage == ModelStages.STAGING

        model_version = client_with_model.get_model_version(
            self.MODEL_NAME, "new name"
        )

        assert model_version.name == "new name"
        assert model_version.number == 1
        assert model_version.description == self.VERSION_DESC
        assert model_version.stage == ModelStages.ARCHIVED

    def test_list_model_version(self, client_with_model: "Client"):
        for i in range(PAGE_SIZE_DEFAULT):
            client_with_model.create_model_version(
                self.MODEL_NAME,
                f"{self.VERSION_NAME}_{i}",
                tags=["foo", "bar"],
            )

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME, page=1
        )
        assert len(model_versions) == PAGE_SIZE_DEFAULT

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME, page=2
        )
        assert len(model_versions) == 1

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME, name=f"{self.VERSION_NAME}_{1}"
        )
        assert len(model_versions) == 1

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME, name=f"contains:{self.VERSION_NAME}_"
        )
        assert len(model_versions) == PAGE_SIZE_DEFAULT

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME,
            name=f"contains:{self.VERSION_NAME}_",
            tag="foo",
        )
        assert len(model_versions) == PAGE_SIZE_DEFAULT

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME,
            name=f"contains:{self.VERSION_NAME}_",
            tag="non_existent_tag",
        )
        assert len(model_versions) == 0

        model_versions = client_with_model.list_model_versions(
            self.MODEL_NAME,
            name=f"contains:{self.VERSION_NAME}_",
            tag="",
        )
        assert len(model_versions) == PAGE_SIZE_DEFAULT

    def test_delete_model_version_found(self, client_with_model: "Client"):
        client_with_model.delete_model_version(
            client_with_model.get_model_version(
                self.MODEL_NAME, self.VERSION_NAME
            ).id
        )

        with pytest.raises(KeyError):
            client_with_model.get_model_version(
                self.MODEL_NAME, self.VERSION_NAME
            )

    def test_delete_model_version_not_found(self, client_with_model: "Client"):
        with pytest.raises(KeyError):
            client_with_model.delete_model_version(uuid4())

    def _create_some_model(
        self,
        client: Client,
        model_name: str = "aria_cat_supermodel",
        model_version_name: str = "1.0.0",
    ) -> Model:
        model = client.create_model(
            name=model_name,
        )
        return client.create_model_version(
            model_name_or_id=model.id,
            name=model_version_name,
        ).to_model_class(suppress_class_validation_warnings=True)

    def test_get_by_latest(self, clean_client: "Client"):
        """Test that model can be retrieved with latest."""
        mv1 = self._create_some_model(client=clean_client)

        # latest returns the only model
        mv2 = clean_client.get_model_version(
            model_name_or_id=mv1.model_id,
            model_version_name_or_number_or_id=ModelStages.LATEST,
        ).to_model_class(suppress_class_validation_warnings=True)
        assert mv2 == mv1

        # after second model version, latest should point to it
        mv3 = clean_client.create_model_version(
            model_name_or_id=mv1.model_id, name="2.0.0"
        ).to_model_class(suppress_class_validation_warnings=True)
        mv4 = clean_client.get_model_version(
            model_name_or_id=mv1.model_id,
            model_version_name_or_number_or_id=ModelStages.LATEST,
        ).to_model_class(suppress_class_validation_warnings=True)
        assert mv4 != mv1
        assert mv4 == mv3

    def test_get_by_stage(self, clean_client: "Client"):
        """Test that model can be retrieved by stage."""
        mv1 = self._create_some_model(client=clean_client)

        clean_client.update_model_version(
            version_name_or_id=mv1.id,
            model_name_or_id=mv1.model_id,
            stage=ModelStages.STAGING,
            force=True,
        )

        mv2 = clean_client.get_model_version(
            model_name_or_id=mv1.model_id,
            model_version_name_or_number_or_id=ModelStages.STAGING,
        ).to_model_class(suppress_class_validation_warnings=True)

        assert mv1 == mv2

    def test_stage_not_found(self, clean_client: "Client"):
        """Test that attempting to get model fails if none at the given stage."""
        mv1 = self._create_some_model(client=clean_client)

        with pytest.raises(KeyError):
            clean_client.get_model_version(
                model_name_or_id=mv1.model_id,
                model_version_name_or_number_or_id=ModelStages.STAGING,
            )

    def test_name_and_description_is_mutable(self, clean_client: "Client"):
        """Test that model version name is mutable."""
        model = clean_client.create_model(name=self.MODEL_NAME)
        mv = clean_client.create_model_version(model.id, description="foo")

        mv = clean_client.get_model_version(
            self.MODEL_NAME, ModelStages.LATEST
        )
        assert mv.name == "1"
        assert mv.description == "foo"

        clean_client.update_model_version(
            self.MODEL_NAME, mv.id, name="bar", description="bar"
        )
        mv = clean_client.get_model_version(
            self.MODEL_NAME, ModelStages.LATEST
        )
        assert mv.name == "bar"
        assert mv.description == "bar"
