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

"""Pytest test harness utilities.

This module contains utility functions that connect the pytest tests to the
ZenML test framework. Most of these functions can be used to create fixtures
that are used in the tests.
"""

import logging
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import pytest

from tests.harness.environment import TestEnvironment
from tests.harness.harness import TestHarness
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH, ENV_ZENML_DEBUG
from zenml.login.credentials_store import CredentialsStore
from zenml.stack.stack import Stack


def cleanup_folder(path: str) -> None:
    """Deletes a folder and all its contents in a way that works on Windows.

    Args:
        path: The path to the folder to delete.
    """
    if sys.platform == "win32":
        try:
            shutil.rmtree(path)
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
    else:
        shutil.rmtree(path)


@contextmanager
def environment_session(
    environment_name: Optional[str] = None,
    deployment_name: Optional[str] = None,
    requirements_names: List[str] = [],
    no_provision: bool = False,
    no_teardown: bool = False,
    no_deprovision: bool = False,
) -> Generator[Tuple[TestEnvironment, Client], None, None]:
    """Context manager to provision and use a test environment.

    Use this context manager to provision and use a test environment and
    optionally deprovision and tear it down on exit.

    Args:
        environment_name: The name of the environment to use. If one is not
            provided, an ad-hoc environment will be used.
        deployment_name: Name of the deployment to use. Ignored if an
            environment name is specified.
        requirements_names: List of global test requirements names to use.
            Ignored if an environment name is specified.
        no_provision: Whether to skip environment provisioning (assumes
            environment is already running).
        no_teardown: Whether to skip environment teardown on exit. If the
            environment is already running on entry, it will not be torn down.
        no_deprovision: Whether to skip environment deprovisioning on exit.
            If the environment is already provisioned on entry, it will not be
            deprovisioned on exit.

    Yields:
        The active environment and a client connected with it.
    """
    # set env variables
    os.environ[ENV_ZENML_DEBUG] = "true"
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

    # original working directory
    orig_cwd = os.getcwd()

    harness = TestHarness()

    environment = harness.set_environment(
        environment_name=environment_name,
        deployment_name=deployment_name,
        requirements_names=requirements_names,
    )

    if no_provision:
        logging.info("Skipping environment provisioning")
        with environment.deployment.connect() as client:
            yield environment, client
    else:
        # Provision the environment (bring up the deployment, if local, and
        # register the stacks according to the environment's configuration)
        with environment.setup(
            teardown=not no_teardown,
            deprovision=not no_deprovision,
        ) as client:
            logging.info(
                f"Test session is using environment '{environment.config.name}' "
                f"running at '{client.zen_store.url}'."
            )

            yield environment, client

    # change working directory back to base path
    os.chdir(orig_cwd)


@contextmanager
def clean_repo_session(
    tmp_path_factory: pytest.TempPathFactory,
    repo_path: Optional[str] = None,
    cleanup: bool = True,
) -> Generator[Client, None, None]:
    """Context manager to initialize and use a separate ZenML repository.

    Args:
        tmp_path_factory: A pytest fixture that provides a temporary directory.
        repo_path: The path where to initialize the repository. If one is not
            provided, a repository will be initialized in a temporary directory.
        cleanup: Whether to clean up the repository on exit.

    Yields:
        A ZenML client connected to the repository.
    """
    # original working directory
    orig_cwd = os.getcwd()

    if repo_path is None:
        # change the working directory to a fresh temp path
        dst_path = tmp_path_factory.mktemp("pytest-zenml-repo")
        cleanup = False
    else:
        dst_path = Path(repo_path)

    os.chdir(str(dst_path))

    client = Client()
    orig_root = client.root

    client.initialize(dst_path)
    client.activate_root(dst_path)

    logging.info(f"Tests are running in clean repository: '{dst_path}'")

    yield client

    # remove all traces, and change working directory back to base path
    os.chdir(orig_cwd)
    client.activate_root(orig_root)
    if cleanup:
        cleanup_folder(str(dst_path))


@contextmanager
def clean_project_session(
    tmp_path_factory: pytest.TempPathFactory,
    clean_repo: bool = False,
) -> Generator[Client, None, None]:
    """Context manager to create, activate and use a separate ZenML project.

    Args:
        tmp_path_factory: A pytest fixture that provides a temporary directory.
        clean_repo: Whether to create and use a clean repository for the
            project.

    Yields:
        A ZenML client configured to use the project.
    """
    from zenml.utils.string_utils import random_str

    client = Client()
    original_project = client.active_project.id

    project_name = f"pytest_{random_str(8).lower()}"
    client.create_project(name=project_name, description="pytest test project")

    if clean_repo:
        with clean_repo_session(tmp_path_factory) as repo_client:
            repo_client.set_active_project(project_name)

            logging.info(f"Tests are running in project: '{project_name}'")
            yield repo_client
    else:
        client.set_active_project(project_name)

        logging.info(f"Tests are running in project: '{project_name}'")
        yield client

    # change the active project back to what it was
    client.set_active_project(original_project)
    client.delete_project(project_name)


def build_client_template_dir(template_dir: Path) -> Path:
    """Materialize a clean ZenML client tree at `template_dir`.

    Runs the full Client/GlobalConfiguration init once (alembic
    migrations, default project, default stack) and leaves the
    resulting `zenml/` subtree on disk so that subsequent
    `clean_default_client_session` calls can copy it instead of paying
    the ~15-20s init cost per test. No-op if the template already
    exists.

    Args:
        template_dir: Directory where the template should be created.
            A `zenml/` subdirectory will be populated inside it.

    Returns:
        `template_dir`.
    """
    template_dir.mkdir(parents=True, exist_ok=True)
    template_zenml = template_dir / "zenml"
    if template_zenml.exists():
        return template_dir

    original_config = GlobalConfiguration.get_instance()
    original_client = Client.get_instance()
    original_credentials = CredentialsStore.get_instance()
    orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    orig_cwd = os.getcwd()

    try:
        CredentialsStore.reset_instance()
        GlobalConfiguration._reset_instance()
        Client._reset_instance()

        os.chdir(template_dir)
        os.environ[ENV_ZENML_CONFIG_PATH] = str(template_zenml)
        os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

        gc = GlobalConfiguration()
        gc.analytics_opt_in = False
        client = Client()
        # The template directory isn't itself a ZenML repo root, so
        # Client()._sanitize_config() never touches the store. Force
        # zen_store init explicitly so that the SQLite DB and the
        # default project/stack/user are materialized inside the
        # template tree.
        _ = client.zen_store

        # Seed the per-component `local_stores/<UUID>` directories.
        # `LocalArtifactStore.path` creates the UUID subdir lazily on
        # first property access, but we deliberately avoid going
        # through `client.active_stack` here because that calls
        # `Stack.from_model(...)` which populates a module-level
        # `_STACK_CACHE` in src/zenml/stack/stack.py. A cached Stack
        # instance holds already-initialized component objects, so a
        # subsequent test that mocks `BaseArtifactStore._register`
        # and then calls `active_stack.artifact_store` would hit the
        # cache instead of constructing a fresh instance — breaking
        # e.g. test_register_artifact_store_filesystem.
        #
        # Query the DB directly through the zen_store instead: list
        # the default stack's artifact store components and create
        # each `local_stores_path / <component_id>` folder. No
        # Stack.from_model, no BaseArtifactStore.__init__, no
        # _STACK_CACHE population.
        try:
            from zenml.enums import StackComponentType
            from zenml.models import ComponentFilter

            local_stores_root = Path(gc.local_stores_path)
            filter_model = ComponentFilter(
                type=StackComponentType.ARTIFACT_STORE,
            )
            components = client.zen_store.list_stack_components(
                component_filter_model=filter_model,
            )
            for component in components.items:
                (local_stores_root / str(component.id)).mkdir(
                    parents=True, exist_ok=True
                )
        except Exception as e:  # noqa: BLE001
            logging.warning(
                "Failed to pre-create artifact store path in "
                "template: %s",
                e,
            )
    finally:
        os.chdir(orig_cwd)
        if orig_config_path is not None:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        elif ENV_ZENML_CONFIG_PATH in os.environ:
            del os.environ[ENV_ZENML_CONFIG_PATH]
        GlobalConfiguration._reset_instance(original_config)
        Client._reset_instance(original_client)
        CredentialsStore.reset_instance(original_credentials)

    return template_dir


@contextmanager
def clean_default_client_session(
    tmp_path_factory: pytest.TempPathFactory,
    template_dir: Optional[Path] = None,
) -> Generator[Client, None, None]:
    """Context manager to initialize and use a clean local default ZenML client.

    This context manager creates a clean ZenML client with its own global
    configuration and local database.

    Args:
        tmp_path_factory: A pytest fixture that provides a temporary directory.
        template_dir: Optional directory containing a pre-built `zenml/`
            template (see [`build_client_template_dir`][]). When supplied,
            the template is copied into the per-test directory instead of
            running the full alembic migration cycle, reducing per-test
            setup from ~15-20s to ~0.1s.

    Yields:
        A clean ZenML client.
    """
    # save the current global configuration and client singleton instances
    # to restore them later, then reset them. Everything between here and
    # the `finally` must be unwound no matter what: previous versions of
    # this function relied on code-after-yield, which does not run if the
    # body raises. That meant a single failing test could leak the
    # DISABLE_DATABASE_MIGRATION env var into every subsequent test in the
    # same batch, causing cascading "Missing flavor local" / "No user
    # account 'default'" failures when later tests tried to initialize a
    # fresh SqlZenStore with migrations effectively disabled.
    orig_cwd = os.getcwd()
    original_config = GlobalConfiguration.get_instance()
    original_client = Client.get_instance()
    orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    original_credentials = CredentialsStore.get_instance()
    orig_disable_migration = os.getenv("DISABLE_DATABASE_MIGRATION")

    CredentialsStore.reset_instance()
    GlobalConfiguration._reset_instance()
    Client._reset_instance()

    # src/zenml/stack/stack.py keeps a module-level `_STACK_CACHE`
    # keyed on `(stack_id, updated)` that hands out the *same*
    # Stack instance — and therefore the same pre-initialized
    # BaseArtifactStore — across tests that happen to see the same
    # default-stack model. Any test that mocks
    # `BaseArtifactStore._register` expects `active_stack.artifact_store`
    # to run `__init__` fresh; with the cache populated from an
    # earlier test (or from the template build) the mock would never
    # fire. Flush it at the start of every clean_client to guarantee
    # each test gets a fresh Stack.
    try:
        from zenml.stack.stack import _STACK_CACHE

        _STACK_CACHE.clear()
    except Exception:  # noqa: BLE001
        pass

    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("pytest-clean-client")
    os.chdir(tmp_path)

    template_zenml = (
        template_dir / "zenml" if template_dir is not None else None
    )
    used_template = template_zenml is not None and template_zenml.exists()

    try:
        if used_template:
            shutil.copytree(template_zenml, tmp_path / "zenml")
            # The template's config.yaml has absolute paths baked in
            # (database/url/backup_directory all point to the template
            # directory the template was built in). Without rewriting,
            # every test would read/write the template DB instead of its
            # own copy, leaking state across tests. Substitute the
            # template's absolute prefix with this test's tmp_path so
            # paths inside the copied config.yaml resolve to the per-test
            # DB and backup dir.
            #
            # Both prefixes must be passed through Path.resolve() so that
            # symlinks (notably macOS's /tmp -> /private/tmp) are
            # canonicalized identically: zenml stores the resolved path
            # in config.yaml, so old_prefix has to match that form, not
            # the unresolved value the caller may have passed in.
            config_yaml = tmp_path / "zenml" / "config.yaml"
            if config_yaml.exists():
                old_prefix = str(Path(template_dir).resolve())
                new_prefix = str(Path(tmp_path).resolve())
                config_yaml.write_text(
                    config_yaml.read_text().replace(old_prefix, new_prefix)
                )
            # The template DB is already at head; alembic.upgrade() takes
            # ~17s even for a no-op upgrade because it still scans the full
            # history, so explicitly skip migration on the per-test DB.
            os.environ["DISABLE_DATABASE_MIGRATION"] = "true"

        os.environ[ENV_ZENML_CONFIG_PATH] = str(tmp_path / "zenml")
        os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

        # initialize the global config client and store at the new path
        gc = GlobalConfiguration()
        gc.analytics_opt_in = False
        client = Client()
        _ = client.zen_store

        logging.info(f"Tests are running in clean environment: {tmp_path}")

        yield client
    finally:
        # restore the global configuration path
        if orig_config_path is not None:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        else:
            os.environ.pop(ENV_ZENML_CONFIG_PATH, None)

        if orig_disable_migration is not None:
            os.environ["DISABLE_DATABASE_MIGRATION"] = orig_disable_migration
        else:
            os.environ.pop("DISABLE_DATABASE_MIGRATION", None)

        # restore the global configuration, the client and the
        # credentials store
        GlobalConfiguration._reset_instance(original_config)
        Client._reset_instance(original_client)
        CredentialsStore.reset_instance(original_credentials)

        # remove all traces, and change working directory back to base
        # path
        os.chdir(orig_cwd)
        cleanup_folder(str(tmp_path))


def check_test_requirements(
    request: pytest.FixtureRequest,
    environment: Optional[TestEnvironment] = None,
    client: Optional["Client"] = None,
) -> bool:
    """Utility function to check test-level requirements for the current test module.

    If the test requirements are not met, the test is skipped.

    Args:
        request: A pytest fixture request.
        environment: An optional environment providing requirements.
            If not supplied, the active environment will be used.
        client: An optional ZenML client already connected to the
            environment, to be reused. If not provided, a new client will be
            created and configured to connect to the environment.

    Returns:
        True if the test requirements are met, False otherwise.
    """
    harness = TestHarness()
    result, msg = harness.check_requirements(
        module=request.module,
        environment=environment,
        client=client,
    )
    if not result:
        pytest.skip(msg=f"Requirements not met: {msg}")

    return result


@contextmanager
def setup_test_stack_session(
    request: pytest.FixtureRequest,
    tmp_path_factory: Optional[pytest.TempPathFactory] = None,
    environment: Optional[TestEnvironment] = None,
    client: Optional["Client"] = None,
    clean_repo: bool = False,
    check_requirements: bool = True,
    no_cleanup: bool = False,
) -> Generator[Stack, None, None]:
    """Context manager to configure a stack adapted to the requirements of the current test module.

    Args:
        request: A pytest fixture request.
        tmp_path_factory: A pytest fixture that provides a temporary directory.
            This is required if `clean_repo` is True.
        environment: An optional environment to be used to setup the stack.
            If not supplied, the active environment will be used.
        client: An optional ZenML client already connected to the
            environment, to be reused. If not provided, a new client will be
            created and configured to connect to the environment.
        clean_repo: Whether to create and use a clean repository for the
            session.
        check_requirements: Whether to check the test requirements before
            setting up the stack.
        no_cleanup: Whether to skip cleaning up the test stack on exit.

    Yields:
        An active ZenML stack matching the requirements of the test module.

    Raises:
        ValueError: If `tmp_path_factory` is not provided when `clean_repo`
            is True.
    """
    harness = TestHarness()

    if check_requirements:
        check_test_requirements(
            request, environment=environment, client=client
        )

    if clean_repo:
        if not tmp_path_factory:
            raise ValueError(
                "tmp_path_factory is required if clean_repo is True."
            )
        with clean_repo_session(tmp_path_factory) as repo_client:
            with harness.setup_test_stack(
                module=request.module,
                environment=environment,
                client=repo_client,
                cleanup=not no_cleanup,
            ) as stack:
                yield stack
    else:
        with harness.setup_test_stack(
            module=request.module,
            environment=environment,
            client=client,
            cleanup=not no_cleanup,
        ) as stack:
            yield stack
