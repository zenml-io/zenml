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
import base64
import os
import platform
import shutil
import time
from contextlib import ExitStack as does_not_raise
from multiprocessing import Process

import pytest
import requests
import uvicorn
import yaml

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ENV_ZENML_PROFILE_CONFIGURATION,
    REPOSITORY_DIRECTORY_NAME,
    ZEN_SERVICE_ENTRYPOINT,
    ZEN_SERVICE_IP,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator import (
    KubeflowOrchestrator,
)
from zenml.logger import get_logger
from zenml.orchestrators import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)
from zenml.stack import Stack
from zenml.stack.stack_component import StackComponent
from zenml.stack.stack_component_class_registry import (
    StackComponentClassRegistry,
)

from zenml.utils.networking_utils import scan_for_available_port

import os
import platform
import shutil
import time
from multiprocessing import Process

import pytest
import requests
import uvicorn

from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    DEFAULT_SERVICE_START_STOP_TIMEOUT,
    ENV_ZENML_PROFILE_CONFIGURATION,
    REPOSITORY_DIRECTORY_NAME,
    ZEN_SERVICE_ENTRYPOINT,
    ZEN_SERVICE_IP,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_stores import (
    BaseZenStore,
    LocalZenStore,
    RestZenStore,
    SqlZenStore,
)
from zenml.zen_stores.models import StackComponentWrapper, StackWrapper

logger = get_logger(__name__)

not_windows = platform.system() != "Windows"
store_types = [StoreType.LOCAL, StoreType.SQL] + [StoreType.REST] * not_windows


def get_component_from_wrapper(
    wrapper: StackComponentWrapper,
) -> StackComponent:
    """Instantiate a StackComponent from the Configuration."""
    component_class = StackComponentClassRegistry.get_class(
        component_type=wrapper.type, component_flavor=wrapper.flavor
    )
    component_config = yaml.safe_load(base64.b64decode(wrapper.config).decode())
    return component_class.parse_obj(component_config)


@pytest.fixture(params=store_types)
def fresh_zen_store(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> BaseZenStore:
    store_type = request.param
    tmp_path = tmp_path_factory.mktemp(f"{store_type.value}_zen_store")
    os.mkdir(tmp_path / REPOSITORY_DIRECTORY_NAME)

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
        # use environment file to pass profile into the zen service process
        env_file = str(tmp_path / "environ.env")
        with open(env_file, "w") as f:
            f.write(
                f"{ENV_ZENML_PROFILE_CONFIGURATION}='{store_profile.json()}'"
            )
        port = scan_for_available_port(start=8003, stop=9000)
        if not port:
            raise RuntimeError("No available port found.")

        proc = Process(
            target=uvicorn.run,
            args=(ZEN_SERVICE_ENTRYPOINT,),
            kwargs=dict(
                host=ZEN_SERVICE_IP,
                port=port,
                log_level="info",
                env_file=env_file,
            ),
            daemon=True,
        )
        url = f"http://{ZEN_SERVICE_IP}:{port}"
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
            raise RuntimeError("Failed to start ZenService server.")

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
            raise RuntimeError("Failed to shutdown ZenService server.")
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
            StackComponentWrapper.from_component(
                LocalOrchestrator(
                    name="default",
                )
            )
        )

    # but can add one if it has a different name
    zen_store.register_stack_component(
        StackComponentWrapper.from_component(
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

    fresh_zen_store.create_user("aria")
    assert len(fresh_zen_store.users) == 2

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
    fresh_zen_store.create_project("secret_project")
    assert len(fresh_zen_store.projects) == 1

    with pytest.raises(EntityExistsError):
        # project names need to be unique
        fresh_zen_store.create_project("secret_project")
    assert len(fresh_zen_store.projects) == 1

    assert (
        fresh_zen_store.get_project("secret_project").name == "secret_project"
    )
    with pytest.raises(KeyError):
        fresh_zen_store.get_user("integrate_airflow")

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


def test_update_stack_with_new_component(fresh_zen_store):
    """Test updating a stack with a new component"""
    new_orchestrator = LocalOrchestrator(name="new_orchestrator")

    updated_stack = Stack(
        name="default",
        orchestrator=new_orchestrator,
        metadata_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
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
        get_component_from_wrapper(component)
        for component in fresh_zen_store.get_stack_components(
            StackComponentType.ORCHESTRATOR
        )
    ]
    assert new_orchestrator in [
        get_component_from_wrapper(component)
        for component in fresh_zen_store.get_stack("default").components
    ]


def test_update_stack_when_component_not_part_of_stack(
    fresh_zen_store,
):
    """Test adding a new component as part of an existing stack."""
    local_secrets_manager = LocalSecretsManager(name="local_secrets_manager")

    updated_stack = Stack(
        name="default",
        orchestrator=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.ORCHESTRATOR, "default"
            )
        ),
        metadata_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
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
        get_component_from_wrapper(component)
        for component in fresh_zen_store.get_stack_components(
            StackComponentType.SECRETS_MANAGER
        )
    ]
    assert local_secrets_manager in [
        get_component_from_wrapper(component)
        for component in fresh_zen_store.get_stack("default").components
    ]


def test_update_non_existent_stack_raises_error(
    fresh_zen_store,
):
    """Test updating a non-existent stack raises an error."""
    stack = Stack(
        name="aria_is_a_cat_not_a_stack",
        orchestrator=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.ORCHESTRATOR, "default"
            )
        ),
        metadata_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.METADATA_STORE, "default"
            )
        ),
        artifact_store=get_component_from_wrapper(
            fresh_zen_store.get_stack_component(
                StackComponentType.ARTIFACT_STORE, "default"
            )
        ),
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
            StackComponentWrapper.from_component(local_secrets_manager),
        )


def test_update_real_component_succeeds(
    fresh_zen_store,
):
    """Test updating a real component succeeds."""
    kubeflow_orchestrator = StackComponentWrapper.from_component(
        KubeflowOrchestrator(name="arias_orchestrator")
    )
    fresh_zen_store.register_stack_component(kubeflow_orchestrator)

    updated_kubeflow_orchestrator = StackComponentWrapper.from_component(
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

    orchestrator_component = get_component_from_wrapper(
        fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, "arias_orchestrator"
        )
    )
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
            StackComponentWrapper.from_component(
                LocalSecretsManager(name="local_secrets_manager")
            ),
        )


def test_rename_core_stack_component_succeeds(
    fresh_zen_store,
):
    """Test renaming a core stack component succeeds."""
    old_name = "default"
    new_name = "arias_orchestrator"
    renamed_orchestrator = StackComponentWrapper.from_component(
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

    kubeflow_orchestrator = StackComponentWrapper.from_component(
        KubeflowOrchestrator(name=old_name)
    )
    fresh_zen_store.register_stack_component(kubeflow_orchestrator)

    renamed_kubeflow_orchestrator = StackComponentWrapper.from_component(
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

    stack_orchestrator = get_component_from_wrapper(
        fresh_zen_store.get_stack_component(
            StackComponentType.ORCHESTRATOR, new_name
        )
    )

    assert stack_orchestrator is not None
    assert stack_orchestrator.name == new_name
