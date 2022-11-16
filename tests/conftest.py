#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Union
from uuid import uuid4

import pytest
from py._builtin import execfile
from pytest_mock import MockerFixture

from tests.venv_clone_utils import clone_virtualenv
from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_DEBUG, TEST_STEP_INPUT_INT
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
    BaseContainerRegistryConfig,
)
from zenml.enums import ArtifactType, ExecutionStatus, PermissionType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import (
    ArtifactResponseModel,
    PipelineRunResponseModel,
    ProjectRequestModel,
    ProjectResponseModel,
    RoleRequestModel,
    StepRunResponseModel,
    TeamRequestModel,
    UserRequestModel,
    UserResponseModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.pipelines import pipeline
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.post_execution.step import StepView
from zenml.stack.stack import Stack
from zenml.stack.stack_component import StackComponentConfig, StackComponentType
from zenml.steps import StepContext, step
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.sql_zen_store import SqlZenStore, SqlZenStoreConfiguration


@pytest.fixture(scope="module", autouse=True)
def base_client(
    tmp_path_factory: pytest.TempPathFactory,
    session_mocker: MockerFixture,
    request: pytest.FixtureRequest,
):
    """Fixture to get a base clean global configuration and repository for all
    tests."""

    # original working directory
    orig_cwd = os.getcwd()

    # set env variables
    os.environ[ENV_ZENML_DEBUG] = "true"
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)

    # patch the global dir just within the scope of this function
    logging.info(f"Tests are running in path: {tmp_path}")

    # set the ZENML_CONFIG_PATH environment variable to ensure that the global
    # configuration and the local stacks used during testing are separate from
    # those used in the current environment
    os.environ["ZENML_CONFIG_PATH"] = str(tmp_path / "zenml")

    session_mocker.patch("analytics.track")
    session_mocker.patch("analytics.group")
    session_mocker.patch("analytics.identify")

    # initialize global config, repo and zen store at the new path
    GlobalConfiguration()
    client = Client()
    _ = client.zen_store

    # monkey patch original cwd in for later use and yield
    client.original_cwd = orig_cwd
    yield client

    # remove all traces, and change working directory back to base path
    os.chdir(orig_cwd)
    if sys.platform == "win32":
        try:
            shutil.rmtree(tmp_path)
        except PermissionError:
            # Windows does not have the concept of unlinking a file and deleting
            #  once all processes that are accessing the resource are done
            #  instead windows tries to delete immediately and fails with a
            #  PermissionError: [WinError 32] The process cannot access the
            #  file because it is being used by another process
            logging.debug(
                "Skipping deletion of temp dir at teardown, due to "
                "Windows Permission error"
            )
            # TODO[HIGH]: Implement fixture cleanup for Windows where
            #  shutil.rmtree fails on files that are in use on python 3.7 and
            #  3.8
    else:
        shutil.rmtree(tmp_path)

    # reset the global configuration and the repository
    GlobalConfiguration._reset_instance()
    Client._reset_instance()


@pytest.fixture
def clean_client(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    base_client,
) -> Client:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        request: Pytest FixtureRequest object
        tmp_path_factory: Pytest TempPathFactory in order to create a new
                          temporary directory
        base_repo: Fixture that returns the base_repo that all tests use
    """
    orig_cwd = os.getcwd()
    orig_config_path = os.getenv("ZENML_CONFIG_PATH")

    # change the working directory to a fresh temp path
    test_name = request.node.name
    test_name = test_name.replace("[", "-").replace("]", "-")
    tmp_path = tmp_path_factory.mktemp(test_name)

    os.chdir(tmp_path)

    logging.info(f"Tests are running in clean environment: {tmp_path}")

    # save the current global configuration and repository singleton instances
    # to restore them later, then reset them
    original_config = GlobalConfiguration.get_instance()
    original_repository = Client.get_instance()
    GlobalConfiguration._reset_instance()
    Client._reset_instance()

    # set the ZENML_CONFIG_PATH environment variable to ensure that the global
    # configuration and the local stacks used in the scope of this function are
    # separate from those used in the global testing environment
    os.environ["ZENML_CONFIG_PATH"] = str(tmp_path / "zenml")

    # initialize global config, repo and zen store at the new path
    GlobalConfiguration()
    client = Client()
    _ = client.zen_store

    # monkey patch base repo cwd for later user and yield
    client.original_cwd = base_client.original_cwd

    yield client

    # remove all traces, and change working directory back to base path
    os.chdir(orig_cwd)
    if sys.platform == "win32":
        try:
            shutil.rmtree(tmp_path)
        except PermissionError:
            # Windows does not have the concept of unlinking a file and deleting
            #  once all processes that are accessing the resource are done
            #  instead windows tries to delete immediately and fails with a
            #  PermissionError: [WinError 32] The process cannot access the
            #  file because it is being used by another process
            logging.debug(
                "Skipping deletion of temp dir at teardown, due to "
                "Windows Permission error"
            )
            # TODO[HIGH]: Implement fixture cleanup for Windows where
            #  shutil.rmtree fails on files that are in use on python 3.7 and
            #  3.8
    else:
        shutil.rmtree(tmp_path)

    # restore the global configuration path
    os.environ["ZENML_CONFIG_PATH"] = orig_config_path

    # restore the original global configuration and the repository singleton
    GlobalConfiguration._reset_instance(original_config)
    Client._reset_instance(original_repository)


@pytest.fixture
def sql_store() -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
    temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
        ),
        track_analytics=False,
    )
    default_project = store.list_projects()[0]
    default_stack = store.list_stacks()[0]
    active_user = store.list_users()[0]
    yield {
        "store": store,
        "default_project": default_project,
        "default_stack": default_stack,
        "active_user": active_user,
    }


@pytest.fixture
def sql_store_with_run() -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
    temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")

    GlobalConfiguration().set_store(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
        ),
    )
    store = GlobalConfiguration().zen_store

    default_project = store.list_projects()[0]
    default_stack = store.list_stacks()[0]
    active_user = store.list_users()[0]

    @step
    def step_one() -> int:
        return TEST_STEP_INPUT_INT

    @step
    def step_two(input: int) -> int:
        return input + 1

    @pipeline
    def test_pipeline(step_one, step_two):
        value = step_one()
        step_two(value)

    test_pipeline(step_one=step_one(), step_two=step_two()).run()
    pipeline_run = store.list_runs()[0]
    pipeline_step = store.list_run_steps(pipeline_run.id)[1]

    yield {
        "store": store,
        "default_project": default_project,
        "default_stack": default_stack,
        "active_user": active_user,
        "pipeline_run": pipeline_run,
        "step": pipeline_step,
    }


@pytest.fixture
def sql_store_with_runs() -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
    temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")

    GlobalConfiguration().set_store(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
        ),
    )
    store = GlobalConfiguration().zen_store

    default_project = store.list_projects()[0]
    default_stack = store.list_stacks()[0]
    active_user = store.list_users()[0]

    @step
    def step_one() -> int:
        return TEST_STEP_INPUT_INT

    @step
    def step_two(input: int) -> int:
        return input + 1

    @pipeline
    def test_pipeline(step_one, step_two):
        value = step_one()
        step_two(value)

    for _ in range(10):
        test_pipeline(step_one=step_one(), step_two=step_two()).run()

    pipeline_runs = store.list_runs()

    yield {
        "store": store,
        "default_project": default_project,
        "default_stack": default_stack,
        "active_user": active_user,
        "pipeline_runs": pipeline_runs,
    }


@pytest.fixture
def sql_store_with_team() -> Dict[str, Union[BaseZenStore, BaseResponseModel]]:
    temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
        ),
        track_analytics=False,
    )
    new_team = TeamRequestModel(name="arias_team")
    store.create_team(new_team)
    default_project = store.list_projects()[0]
    default_stack = store.list_stacks()[0]
    active_user = store.list_users()[0]
    default_team = store.list_teams()[0]
    yield {
        "store": store,
        "default_project": default_project,
        "default_stack": default_stack,
        "active_user": active_user,
        "default_team": default_team,
    }


@pytest.fixture
def sql_store_with_user_team_role() -> Dict[
    str, Union[BaseZenStore, BaseResponseModel]
]:
    temp_dir = tempfile.TemporaryDirectory(suffix="_zenml_sql_test")

    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{Path(temp_dir.name) / 'store.db'}"
        ),
        track_analytics=False,
    )

    new_team = TeamRequestModel(name="axls_team")
    new_team = store.create_team(new_team)

    new_role = RoleRequestModel(
        name="axl_feeder", permissions={PermissionType.ME}
    )
    new_role = store.create_role(new_role)

    new_user = UserRequestModel(name="axl")
    new_user = store.create_user(new_user)

    new_project = ProjectRequestModel(name="axl_prj")
    new_project = store.create_project(new_project)

    yield {
        "store": store,
        "user": new_user,
        "team": new_team,
        "role": new_role,
        "project": new_project,
    }


@pytest.fixture
def files_dir(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """Fixture that will search for a folder with the same name as the test
    file and move it into the temp path of the test.

    |dir
    |--test_functionality
    |--|--test_specific_method
    |--test_functionality.py#test_specific_method

    In this case if the `test_specific_method()` function inside the
    `test_functionality.py` has this fixture, the
    `test_functionality/test_specific_method` file is copied into the tmp_path.
    The path is passed into the test_specific_method(datadir: str) as string.

    TO use this, ensure the filename (minus '.py') corresponds to the outer
    directory name. And the inner directory corresponds to the test methods
    name.

    Returns:
        tmp_path at which to find the files.
    """
    filename = Path(request.module.__file__)
    test_dir = filename.with_suffix("")

    test_name = request.function.__name__

    tmp_path = tmp_path / test_name

    if os.path.isdir(test_dir):
        test_function_dir = test_dir / test_name
        if os.path.isdir(test_function_dir):
            shutil.copytree(test_function_dir, tmp_path)

    return tmp_path


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
        project=uuid4(),
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
        project=uuid4(),
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
        project=uuid4(),
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
        project=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def remote_artifact_store():
    """Fixture that creates a local artifact store for testing."""
    from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (
        GCPArtifactStore,
    )
    from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
        GCPArtifactStoreConfig,
    )

    return GCPArtifactStore(
        name="",
        id=uuid4(),
        config=GCPArtifactStoreConfig(path="gs://bucket"),
        flavor="gcp",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        project=uuid4(),
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
        project=uuid4(),
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
        flavor="default",
        type=StackComponentType.CONTAINER_REGISTRY,
        user=uuid4(),
        project=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def empty_step():
    """Pytest fixture that returns an empty (no input, no output) step."""

    @step
    def _empty_step() -> None:
        pass

    return _empty_step


@pytest.fixture
def generate_empty_steps():
    """Pytest fixture that returns a function that generates multiple empty
    steps."""

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
    """Pytest fixture that returns a pipeline which takes a single step
    named `step_`."""

    @pipeline
    def _pipeline(step_):
        step_()

    return _pipeline


@pytest.fixture
def unconnected_two_step_pipeline():
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2`. The steps are not connected to each other."""

    @pipeline
    def _pipeline(step_1, step_2):
        step_1()
        step_2()

    return _pipeline


@pytest.fixture
def int_step_output():
    @step
    def _step() -> int:
        return 1

    return _step()()


@pytest.fixture
def step_with_two_int_inputs():
    @step
    def _step(input_1: int, input_2: int) -> None:
        pass

    return _step


@pytest.fixture
def step_context_with_no_output():
    return StepContext(
        step_name="", output_materializers={}, output_artifacts={}
    )


@pytest.fixture
def step_context_with_single_output():
    materializers = {"output_1": BaseMaterializer}
    artifacts = {"output_1": BaseArtifact()}

    return StepContext(
        step_name="",
        output_materializers=materializers,
        output_artifacts=artifacts,
    )


@pytest.fixture
def step_context_with_two_outputs():
    materializers = {
        "output_1": BaseMaterializer,
        "output_2": BaseMaterializer,
    }
    artifacts = {"output_1": BaseArtifact(), "output_2": BaseArtifact()}

    return StepContext(
        step_name="",
        output_materializers=materializers,
        output_artifacts=artifacts,
    )


@pytest.fixture
def sample_user_model() -> UserResponseModel:
    """Return a sample user model for testing purposes"""
    return UserResponseModel(
        id=uuid4(),
        name="axl",
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def sample_project_model() -> ProjectResponseModel:
    """Return a sample project model for testing purposes"""
    return ProjectResponseModel(
        id=uuid4(),
        name="axl",
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def sample_step_model(
    sample_user_model: UserResponseModel,
    sample_project_model: ProjectResponseModel,
) -> StepRunResponseModel:
    """Return a sample step model for testing purposes"""
    return StepRunResponseModel(
        id=uuid4(),
        name="sample_step",
        parents_step_ids=[0],
        entrypoint_name="sample_entrypoint",
        parameters={},
        mlmd_parent_step_ids=[],
        pipeline_run_id=uuid4(),
        parent_step_ids=[],
        input_artifacts={},
        step_configuration={},
        status=ExecutionStatus.COMPLETED,
        created=datetime.now(),
        updated=datetime.now(),
        user=sample_user_model,
        project=sample_project_model,
        docstring="",
        mlmd_id=0,
    )


@pytest.fixture
def sample_step_view(sample_step_model) -> StepView:
    """Return a sample step view for testing purposes"""
    return StepView(sample_step_model)


@pytest.fixture
def sample_pipeline_run_model(
    sample_user_model: UserResponseModel,
    sample_project_model: ProjectResponseModel,
) -> PipelineRunResponseModel:
    """Return sample pipeline run view for testing purposes"""
    return PipelineRunResponseModel(
        id=uuid4(),
        name="sample_run_name",
        pipeline_configuration={},
        num_steps=1,
        status=ExecutionStatus.COMPLETED,
        created=datetime.now(),
        updated=datetime.now(),
        user=sample_user_model,
        project=sample_project_model,
    )


@pytest.fixture
def sample_pipeline_run_view(
    sample_step_view, sample_pipeline_run_model
) -> PipelineRunView:
    """Return sample pipeline run view for testing purposes"""
    sample_pipeline_run_view = PipelineRunView(sample_pipeline_run_model)
    setattr(
        sample_pipeline_run_view,
        "_steps",
        {sample_step_view.name: sample_step_view},
    )
    return sample_pipeline_run_view


@pytest.fixture
def sample_artifact_model() -> ArtifactResponseModel:
    """Return a sample artifact model for testing purposes"""
    return ArtifactResponseModel(
        id=uuid4(),
        name="sample_artifact",
        uri="sample_uri",
        type=ArtifactType.DATA,
        materializer="sample_materializer",
        data_type="sample_data_type",
        parent_step_id=uuid4(),
        producer_step_id=uuid4(),
        is_cached=False,
    )


@pytest.fixture
def virtualenv(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> str:
    """Based on the underlying virtual environment a copy of the environment is
    made and used for the test that uses this fixture.

    Args:
        request: Pytest FixtureRequest object used to create unique tmp dir
                 based on the name of the test
        tmp_path_factory: Pytest TempPathFactory in order to create a new
                          temporary directory

    Yields:
        Path to the virtual environment
    """
    if request.config.getoption("use_virtualenv"):
        # Remember the old executable
        orig_sys_executable = Path(sys.executable)

        test_name = request.node.name
        test_name = test_name.replace("[", "-").replace("]", "-")

        # Create temporary venv
        tmp_path = tmp_path_factory.mktemp(test_name) / "venv"
        # TODO[ENG-707]: Implement for use outside of a base virtual environment
        #  If this happens outside of a virtual environment the complete
        #  /usr space is cloned
        clone_virtualenv(
            src_dir=str(orig_sys_executable.parent.parent),
            dst_dir=str(tmp_path),
        )

        env_bin_dir = "bin"
        if sys.platform == "win32":
            env_bin_dir = "Scripts"

        # Activate venv
        activate_this_file = tmp_path / env_bin_dir / "activate_this.py"

        if not activate_this_file.is_file():
            raise FileNotFoundError(
                "Integration tests don't work for some local "
                "virtual environments. Use virtualenv for "
                "your virtual environment to run integration "
                "tests"
            )

        execfile(
            str(activate_this_file), dict(__file__=str(activate_this_file))
        )

        # Set new system executable
        sys.executable = tmp_path / env_bin_dir / "python"

        yield tmp_path
        # Reset system executable
        sys.executable = orig_sys_executable

        # Switch back to original venv
        activate_this_f = Path(orig_sys_executable).parent / "activate_this.py"

        if not activate_this_f.is_file():
            raise FileNotFoundError(
                "Integration tests don't work for some local "
                "virtual environments. Use virtualenv for "
                "your virtual environment to run integration "
                "tests"
            )
        execfile(str(activate_this_f), dict(__file__=str(activate_this_f)))

    else:
        yield ""


def pytest_addoption(parser):
    """Fixture that gets called by pytest ahead of tests. Adds the following cli
    option:

        * an option to enable kubeflow for integration tests
        * an option to disable the use of the virtualenv fixture. This might be
        useful for local integration testing in case you do not care about your
        base environment being affected
        * an option to use a specific secrets manager flavor in the secrets
        manager integration tests

    How to use this option:

        ```pytest tests/integration/test_examples.py --on-kubeflow```

        ```pytest tests/integration/test_examples.py --use-virtualenv```

        ```pytest tests/integration/test_examples.py --secrets-manager-flavor aws```

    """
    parser.addoption(
        "--on-kubeflow",
        action="store_true",
        default=False,
        help="Only run Kubeflow",
    )
    parser.addoption(
        "--use-virtualenv",
        action="store_true",
        default=False,
        help="Run Integration tests in cloned env",
    )
    parser.addoption(
        "--secrets-manager-flavor",
        action="store",
        default="local",
        help="The flavor of secrets manager to use (local, aws, etc)",
    )


def pytest_generate_tests(metafunc):
    """Parametrizes the repo_fixture_name wherever it is imported by a step with
    the cli options."""
    if "repo_fixture_name" in metafunc.fixturenames:
        if metafunc.config.getoption("on_kubeflow"):
            repos = ["clean_kubeflow_repo"]
        else:
            repos = ["clean_base_repo"]
        metafunc.parametrize("repo_fixture_name", repos)
