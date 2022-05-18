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
import platform
import shutil
import time
from contextlib import ExitStack as does_not_raise
from multiprocessing import Process
from uuid import uuid4

import pytest
import requests
import uvicorn

from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_PROFILE_NAME,
    REPOSITORY_DIRECTORY_NAME,
    ZEN_SERVER_ENTRYPOINT,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator import (
    KubeflowOrchestrator,
)
from zenml.logger import get_logger
from zenml.orchestrators import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)
from zenml.stack import Stack
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_stores import (
    BaseZenStore,
    LocalZenStore,
    RestZenStore,
    SqlZenStore,
)
from zenml.zen_stores.models import ComponentWrapper, StackWrapper
from zenml.zen_stores.models.pipeline_models import (
    PipelineRunWrapper,
    PipelineWrapper,
)

logger = get_logger(__name__)

test_rest = (
    platform.system() != "Windows" and "ZENML_SKIP_TEST_REST" not in os.environ
)
store_types = [StoreType.LOCAL, StoreType.SQL] + [StoreType.REST] * test_rest


@pytest.fixture(params=store_types)
def fresh_zen_store(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> BaseZenStore:
    store_type = request.param
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_zen_store")
    os.mkdir(tmp_path / REPOSITORY_DIRECTORY_NAME)

    global_cfg = GlobalConfiguration()

    if store_type == StoreType.LOCAL:
        yield LocalZenStore().initialize(str(tmp_path))
    elif store_type == StoreType.SQL:
        yield SqlZenStore().initialize(f"sqlite:///{tmp_path / 'store.db'}")
    elif store_type == StoreType.REST:
        # create temporary zen store and profile configuration for unit tests
        backing_zen_store = LocalZenStore().initialize(str(tmp_path))
        store_profile = ProfileConfiguration(
            name=f"test_profile_{hash(str(tmp_path))}",
            store_url=backing_zen_store.url,
            store_type=backing_zen_store.type,
        )
        global_cfg.add_or_update_profile(store_profile)
        # use environment file to pass profile into the zen service process
        env_file = str(tmp_path / "environ.env")
        with open(env_file, "w") as f:
            f.write(f"{ENV_ZENML_PROFILE_NAME}='{store_profile.name}'\n")
            f.write(
                f"{ENV_ZENML_CONFIG_PATH}='{global_cfg.config_directory}'\n"
            )

        port = scan_for_available_port(start=8003, stop=9000)
        if not port:
            raise RuntimeError("No available port found.")

        proc = Process(
            target=uvicorn.run,
            args=(ZEN_SERVER_ENTRYPOINT,),
            kwargs=dict(
                host=DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
                port=port,
                log_level="info",
                env_file=env_file,
            ),
            daemon=True,
        )
        url = f"http://{DEFAULT_LOCAL_SERVICE_IP_ADDRESS}:{port}"
        proc.start()

        # wait 10 seconds for server to start
        for t in range(DEFAULT_SERVICE_START_STOP_TIMEOUT):
            try:
                if requests.head(f"{url}/health").status_code == 200:
                    break
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1)
        else:
            proc.kill()
            raise RuntimeError("Failed to start ZenServer.")
        yield RestZenStore().initialize(url)

        # make sure there's still a server and tear down
        assert proc.is_alive()
        proc.kill()
        # wait 10 seconds for process to be killed:
        for t in range(DEFAULT_SERVICE_START_STOP_TIMEOUT):
            if proc.is_alive():
                time.sleep(1)
            else:
                break
        else:
            raise RuntimeError("Failed to shutdown ZenServer.")

        global_cfg.delete_profile(store_profile.name)
    else:
        raise NotImplementedError(f"No ZenStore for {store_type}")

    shutil.rmtree(tmp_path)


def test_register_deregister_stacks(fresh_zen_store):
    """Test creating a new zen store."""
    stack = Stack.default_local_stack()

    # zen store is pre-initialized with the default stack
    zen_store = fresh_zen_store
    assert len(zen_store.stacks) == 1
    assert len(zen_store.stack_configurations) == 1

    # retrieve the default stack
    got_stack = zen_store.get_stack(stack.name)
    assert got_stack.name == stack.name
    stack_configuration = zen_store.get_stack_configuration(stack.name)
    assert set(stack_configuration) == {
        "orchestrator",
        "metadata_store",
        "artifact_store",
    }
    assert stack_configuration[StackComponentType.ORCHESTRATOR] == "default"

    # can't register the same stack twice or another stack with the same name
    with pytest.raises(StackExistsError):
        zen_store.register_stack(StackWrapper.from_stack(stack))
    with pytest.raises(StackExistsError):
        zen_store.register_stack(StackWrapper(name=stack.name, components=[]))

    # can't remove a stack that doesn't exist:
    with pytest.raises(KeyError):
        zen_store.deregister_stack("overflow")

    # remove the default stack
    zen_store.deregister_stack(stack.name)
    assert len(zen_store.stacks) == 0
    with pytest.raises(KeyError):
        _ = zen_store.get_stack(stack.name)

    # now can add another stack with the same name
    zen_store.register_stack(StackWrapper(name=stack.name, components=[]))
    assert len(zen_store.stacks) == 1


def test_register_deregister_components(fresh_zen_store):
    """Test adding and removing stack components."""
    required_components = {
        StackComponentType.ARTIFACT_STORE,
        StackComponentType.METADATA_STORE,
        StackComponentType.ORCHESTRATOR,
    }

    # zem store starts off with the default stack
    zen_store = fresh_zen_store
    for component_type in StackComponentType:
        component_type = StackComponentType(component_type)
        if component_type in required_components:
            assert len(zen_store.get_stack_components(component_type)) == 1
        else:
            assert len(zen_store.get_stack_components(component_type)) == 0

    # get a component
    orchestrator = zen_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )

    assert orchestrator.flavor == "local"
    assert orchestrator.name == "default"

    # can't add another orchestrator of same name
    with pytest.raises(StackComponentExistsError):
        zen_store.register_stack_component(
            ComponentWrapper.from_component(
                LocalOrchestrator(
                    name="default",
                )
            )
        )

    # but can add one if it has a different name
    zen_store.register_stack_component(
        ComponentWrapper.from_component(
            LocalOrchestrator(
                name="local_orchestrator_part_2_the_remix",
            )
        )
    )
    assert (
        len(zen_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 2
    )

    # can't delete an orchestrator that's part of a stack
    with pytest.raises(ValueError):
        zen_store.deregister_stack_component(
            StackComponentType.ORCHESTRATOR, "default"
        )

    # but can if the stack is deleted first
    zen_store.deregister_stack("default")
    zen_store.deregister_stack_component(
        StackComponentType.ORCHESTRATOR, "default"
    )
    assert (
        len(zen_store.get_stack_components(StackComponentType.ORCHESTRATOR))
        == 1
    )


def test_user_management(fresh_zen_store):
    """Tests user creation and deletion."""
    # starts with a default user
    assert len(fresh_zen_store.users) == 1

    assert fresh_zen_store.users[0].name == "default"
    default_user = fresh_zen_store.get_user("default")
    assert default_user.id == fresh_zen_store.users[0].id

    created_user_id = fresh_zen_store.create_user("aria").id
    assert len(fresh_zen_store.users) == 2

    retrieved_user_id = fresh_zen_store.get_user("aria").id
    assert created_user_id == retrieved_user_id

    with pytest.raises(EntityExistsError):
        # usernames need to be unique
        fresh_zen_store.create_user("aria")
    assert len(fresh_zen_store.users) == 2

    assert fresh_zen_store.get_user("aria").name == "aria"
    with pytest.raises(KeyError):
        fresh_zen_store.get_user("not_aria")

    fresh_zen_store.create_team("team_aria")
    fresh_zen_store.add_user_to_team(team_name="team_aria", user_name="aria")

    fresh_zen_store.create_role("cat")
    fresh_zen_store.assign_role(
        role_name="cat", entity_name="aria", is_user=True
    )

    assert len(fresh_zen_store.get_users_for_team("team_aria")) == 1
    assert len(fresh_zen_store.role_assignments) == 1

    # Deletes the user as well as any team/role assignment
    fresh_zen_store.delete_user("aria")
    assert len(fresh_zen_store.users) == 1
    assert len(fresh_zen_store.get_users_for_team("team_aria")) == 0
    assert len(fresh_zen_store.role_assignments) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent user
        fresh_zen_store.delete_user("aria")


def test_team_management(fresh_zen_store):
    """Tests team creation and deletion."""
    fresh_zen_store.create_user("adam")
    fresh_zen_store.create_user("hamza")
    fresh_zen_store.create_team("zenml")
    assert len(fresh_zen_store.teams) == 1

    with pytest.raises(EntityExistsError):
        # team names need to be unique
        fresh_zen_store.create_team("zenml")
    assert len(fresh_zen_store.teams) == 1

    assert fresh_zen_store.get_team("zenml").name == "zenml"
    with pytest.raises(KeyError):
        fresh_zen_store.get_team("mlflow")

    fresh_zen_store.add_user_to_team(team_name="zenml", user_name="adam")
    fresh_zen_store.add_user_to_team(team_name="zenml", user_name="hamza")
    assert len(fresh_zen_store.get_users_for_team("zenml")) == 2

    with pytest.raises(KeyError):
        # non-existent team
        fresh_zen_store.add_user_to_team(team_name="airflow", user_name="hamza")

    with pytest.raises(KeyError):
        # non-existent user
        fresh_zen_store.add_user_to_team(team_name="zenml", user_name="elon")

    fresh_zen_store.remove_user_from_team(team_name="zenml", user_name="hamza")
    assert len(fresh_zen_store.get_users_for_team("zenml")) == 1

    fresh_zen_store.delete_team("zenml")
    assert len(fresh_zen_store.get_teams_for_user("adam")) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent team
        fresh_zen_store.delete_team("zenml")


def test_project_management(fresh_zen_store):
    """Tests project creation and deletion."""
    project = fresh_zen_store.create_project("secret_project")
    assert len(fresh_zen_store.projects) == 1
    assert fresh_zen_store.projects[0].name == "secret_project"
    assert fresh_zen_store.projects[0].id == project.id

    with pytest.raises(EntityExistsError):
        # project names need to be unique
        fresh_zen_store.create_project("secret_project")
    assert len(fresh_zen_store.projects) == 1

    with pytest.raises(KeyError):
        fresh_zen_store.get_user("integrate_airflow")
    retrieved = fresh_zen_store.get_project("secret_project")
    assert retrieved.name == "secret_project"
    assert retrieved.id == project.id

    fresh_zen_store.delete_project("secret_project")
    assert len(fresh_zen_store.projects) == 0

    with pytest.raises(KeyError):
        # can't delete non-existent project
        fresh_zen_store.delete_project("secret_project")


def test_role_management(fresh_zen_store):
    """Tests role creation, deletion, assignment and revocation."""
    fresh_zen_store.create_user("aria")
    fresh_zen_store.create_team("cats")
    fresh_zen_store.add_user_to_team(user_name="aria", team_name="cats")
    fresh_zen_store.create_role("beautiful")
    assert len(fresh_zen_store.roles) == 1

    with pytest.raises(EntityExistsError):
        # role names need to be unique
        fresh_zen_store.create_role("beautiful")
    assert len(fresh_zen_store.roles) == 1

    assert fresh_zen_store.get_role("beautiful").name == "beautiful"
    with pytest.raises(KeyError):
        fresh_zen_store.get_role("office_cat")

    fresh_zen_store.assign_role(
        role_name="beautiful", entity_name="aria", is_user=True
    )

    assert (
        len(fresh_zen_store.get_role_assignments_for_user(user_name="aria"))
        == 1
    )

    fresh_zen_store.assign_role(
        role_name="beautiful", entity_name="cats", is_user=False
    )

    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=False
            )
        )
        == 1
    )
    assert (
        len(fresh_zen_store.get_role_assignments_for_team(team_name="cats"))
        == 1
    )
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=True
            )
        )
        == 2
    )

    fresh_zen_store.revoke_role(
        role_name="beautiful", entity_name="aria", is_user=True
    )
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=False
            )
        )
        == 0
    )

    fresh_zen_store.delete_team("cats")
    assert (
        len(
            fresh_zen_store.get_role_assignments_for_user(
                user_name="aria", include_team_roles=True
            )
        )
        == 0
    )


def test_flavor_management(fresh_zen_store):
    """Test the management of stack component flavors"""
    # Check for non-existing flavors
    with pytest.raises(KeyError):
        fresh_zen_store.get_flavor_by_name_and_type(
            flavor_name="non_existing_flavor",
            component_type=StackComponentType.ARTIFACT_STORE,
        )

    # Check whether the registration of new flavors is working as intended
    fresh_zen_store.create_flavor(
        name="test",
        source="test_artifact_store.TestArtifactStore",
        stack_component_type=StackComponentType.ARTIFACT_STORE,
    )

    # Duplicated registration should fail with an EntityExistsError
    with pytest.raises(EntityExistsError):
        fresh_zen_store.create_flavor(
            name="test",
            source="test_artifact_store.TestArtifactStore",
            stack_component_type=StackComponentType.ARTIFACT_STORE,
        )

    # Ensure that the get_flavors_by_type is working as intended
    new_artifact_store_flavors = fresh_zen_store.get_flavors_by_type(
        StackComponentType.ARTIFACT_STORE
    )
    assert new_artifact_store_flavors

    # Ensure that the newly registered flavor can be accessed.
    new_artifact_store_flavor = fresh_zen_store.get_flavor_by_name_and_type(
        flavor_name="test",
        component_type=StackComponentType.ARTIFACT_STORE,
    )
    assert new_artifact_store_flavor


def test_update_stack_with_new_component(fresh_zen_store):
    """Test updating a stack with a new component"""
    new_orchestrator = LocalOrchestrator(name="new_orchestrator")

    updated_stack = Stack(
        name="default",
        orchestrator=new_orchestrator,
        metadata_store=fresh_zen_store.get_stack_component(
            StackComponentType.METADATA_STORE, "default"
        ).to_component(),
        artifact_store=fresh_zen_store.get_stack_component(
            StackComponentType.ARTIFACT_STORE, "default"
        ).to_component(),
    )
    try:
        fresh_zen_store.update_stack(
            updated_stack.name, StackWrapper.from_stack(updated_stack)
        )
    except KeyError:
        pytest.fail("Failed to update stack")

    assert (
        len(
            fresh_zen_store.get_stack_components(
                StackComponentType.ORCHESTRATOR
            )
        )
        == 2
    )
    assert new_orchestrator in [
        wrapper.to_component()
        for wrapper in fresh_zen_store.get_stack_components(
            StackComponentType.ORCHESTRATOR
        )
    ]
    assert new_orchestrator in [
        wrapper.to_component()
        for wrapper in fresh_zen_store.get_stack("default").components
    ]


def test_update_stack_when_component_not_part_of_stack(
    fresh_zen_store,
):
    """Test adding a new component as part of an existing stack."""
    local_secrets_manager = LocalSecretsManager(name="local_secrets_manager")

    updated_stack = Stack(
        name="default",
        orchestrator=fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, "default"
        ).to_component(),
        metadata_store=fresh_zen_store.get_stack_component(
            StackComponentType.METADATA_STORE, "default"
        ).to_component(),
        artifact_store=fresh_zen_store.get_stack_component(
            StackComponentType.ARTIFACT_STORE, "default"
        ).to_component(),
        secrets_manager=local_secrets_manager,
    )

    with does_not_raise():
        fresh_zen_store.update_stack(
            updated_stack.name, StackWrapper.from_stack(updated_stack)
        )

    assert (
        len(
            fresh_zen_store.get_stack_components(
                StackComponentType.SECRETS_MANAGER
            )
        )
        == 1
    )
    assert local_secrets_manager in [
        wrapper.to_component()
        for wrapper in fresh_zen_store.get_stack_components(
            StackComponentType.SECRETS_MANAGER
        )
    ]
    assert local_secrets_manager in [
        wrapper.to_component()
        for wrapper in fresh_zen_store.get_stack("default").components
    ]


def test_update_non_existent_stack_raises_error(
    fresh_zen_store,
):
    """Test updating a non-existent stack raises an error."""
    stack = Stack(
        name="aria_is_a_cat_not_a_stack",
        orchestrator=fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, "default"
        ).to_component(),
        metadata_store=fresh_zen_store.get_stack_component(
            StackComponentType.METADATA_STORE, "default"
        ).to_component(),
        artifact_store=fresh_zen_store.get_stack_component(
            StackComponentType.ARTIFACT_STORE, "default"
        ).to_component(),
    )

    with pytest.raises(KeyError):
        fresh_zen_store.update_stack(
            "aria_is_a_cat_not_a_stack", StackWrapper.from_stack(stack)
        )


def test_update_non_existent_stack_component_raises_error(
    fresh_zen_store,
):
    """Test updating a non-existent stack component raises an error."""
    local_secrets_manager = LocalSecretsManager(name="local_secrets_manager")

    with pytest.raises(KeyError):
        fresh_zen_store.update_stack_component(
            local_secrets_manager.name,
            StackComponentType.SECRETS_MANAGER,
            ComponentWrapper.from_component(local_secrets_manager),
        )


def test_update_real_component_succeeds(
    fresh_zen_store,
):
    """Test updating a real component succeeds."""
    kubeflow_orchestrator = ComponentWrapper.from_component(
        KubeflowOrchestrator(name="arias_orchestrator")
    )
    fresh_zen_store.register_stack_component(kubeflow_orchestrator)

    updated_kubeflow_orchestrator = ComponentWrapper.from_component(
        KubeflowOrchestrator(
            name="arias_orchestrator",
            custom_docker_base_image_name="aria/arias_base_image",
        )
    )
    fresh_zen_store.update_stack_component(
        "arias_orchestrator",
        StackComponentType.ORCHESTRATOR,
        updated_kubeflow_orchestrator,
    )

    orchestrator_component = fresh_zen_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, "arias_orchestrator"
    ).to_component()

    assert (
        orchestrator_component.custom_docker_base_image_name
        == "aria/arias_base_image"
    )


def test_rename_nonexistent_stack_component_fails(
    fresh_zen_store,
):
    """Test renaming a non-existent stack component fails."""
    with pytest.raises(KeyError):
        fresh_zen_store.update_stack_component(
            "not_a_secrets_manager",
            StackComponentType.SECRETS_MANAGER,
            ComponentWrapper.from_component(
                LocalSecretsManager(name="local_secrets_manager")
            ),
        )


def test_rename_core_stack_component_succeeds(
    fresh_zen_store,
):
    """Test renaming a core stack component succeeds."""
    old_name = "default"
    new_name = "arias_orchestrator"
    renamed_orchestrator = ComponentWrapper.from_component(
        LocalOrchestrator(name=new_name)
    )
    fresh_zen_store.update_stack_component(
        old_name, StackComponentType.ORCHESTRATOR, renamed_orchestrator
    )
    with pytest.raises(KeyError):
        assert fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, old_name
        )
    stack_components = fresh_zen_store.get_stack("default").components
    stack_orchestrators = [
        component
        for component in stack_components
        if component.name == new_name
    ]

    assert len(stack_orchestrators) > 0
    assert stack_orchestrators[0].name == new_name


def test_rename_non_core_stack_component_succeeds(
    fresh_zen_store,
):
    """Test renaming a non-core stack component succeeds."""
    old_name = "original_kubeflow"
    new_name = "arias_kubeflow"

    kubeflow_orchestrator = ComponentWrapper.from_component(
        KubeflowOrchestrator(name=old_name)
    )
    fresh_zen_store.register_stack_component(kubeflow_orchestrator)

    renamed_kubeflow_orchestrator = ComponentWrapper.from_component(
        KubeflowOrchestrator(name=new_name)
    )
    fresh_zen_store.update_stack_component(
        old_name,
        StackComponentType.ORCHESTRATOR,
        renamed_kubeflow_orchestrator,
    )

    with pytest.raises(KeyError):
        assert fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, old_name
        )

    stack_orchestrator = fresh_zen_store.get_stack_component(
        StackComponentType.ORCHESTRATOR, new_name
    ).to_component()

    assert stack_orchestrator is not None
    assert stack_orchestrator.name == new_name


def test_pipeline_run_management(
    fresh_zen_store, one_step_pipeline, empty_step
):
    """Test registering and fetching pipeline runs."""
    stack = Stack.default_local_stack()
    pipeline = one_step_pipeline(empty_step())

    run = PipelineRunWrapper(
        name="run_name",
        pipeline=PipelineWrapper.from_pipeline(pipeline),
        stack=StackWrapper.from_stack(stack),
        runtime_configuration={},
        user_id=uuid4(),
        project_name="project",
    )

    fresh_zen_store.register_pipeline_run(run)

    registered_runs = fresh_zen_store.get_pipeline_runs(
        pipeline_name=pipeline.name
    )
    assert len(registered_runs) == 1
    assert registered_runs[0] == run

    assert (
        fresh_zen_store.get_pipeline_run(
            pipeline_name=pipeline.name, run_name=run.name
        )
        == run
    )
    assert (
        fresh_zen_store.get_pipeline_run(
            pipeline_name=pipeline.name,
            run_name=run.name,
            project_name=run.project_name,
        )
        == run
    )

    # Filtering for the wrong projects doesn't return any runs
    assert not fresh_zen_store.get_pipeline_runs(
        pipeline_name=pipeline.name, project_name="not_the_correct_project"
    )
    with pytest.raises(KeyError):
        fresh_zen_store.get_pipeline_run(
            pipeline_name=pipeline.name,
            run_name=run.name,
            project_name="not_the_correct_project",
        )

    # registering a run with the same name fails
    with pytest.raises(EntityExistsError):
        fresh_zen_store.register_pipeline_run(run)

    different_run = run.copy(update={"name": "different_run_name"})
    with does_not_raise():
        fresh_zen_store.register_pipeline_run(different_run)
