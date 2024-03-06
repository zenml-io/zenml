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

import inspect
import logging
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Union,
)
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from tests.harness.environment import TestEnvironment
from tests.harness.harness import TestHarness
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH, ENV_ZENML_DEBUG
from zenml.stack.stack import Stack
from zenml.zen_stores.base_zen_store import BaseZenStore


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
            # TODO[HIGH]: Implement fixture cleanup for Windows where
            #  shutil.rmtree fails on files that are in use on python 3.7 and
            #  3.8
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
def clean_workspace_session(
    tmp_path_factory: pytest.TempPathFactory,
    clean_repo: bool = False,
) -> Generator[Client, None, None]:
    """Context manager to create, activate and use a separate ZenML workspace.

    Args:
        tmp_path_factory: A pytest fixture that provides a temporary directory.
        clean_repo: Whether to create and use a clean repository for the
            workspace.

    Yields:
        A ZenML client configured to use the workspace.
    """
    from zenml.utils.string_utils import random_str

    client = Client()
    original_workspace = client.active_workspace.id

    workspace_name = f"pytest_{random_str(8)}"
    client.create_workspace(
        name=workspace_name, description="pytest test workspace"
    )

    if clean_repo:
        with clean_repo_session(tmp_path_factory) as repo_client:
            repo_client.set_active_workspace(workspace_name)

            logging.info(f"Tests are running in workspace: '{workspace_name}'")
            yield repo_client
    else:
        client.set_active_workspace(workspace_name)

        logging.info(f"Tests are running in workspace: '{workspace_name}'")
        yield client

    # change the active workspace back to what it was
    client.set_active_workspace(original_workspace)
    client.delete_workspace(workspace_name)


class TheMetaZenRemembers(type):
    """The Meta Class to create TheZenRemembers class."""

    def __getattr__(self, name: str) -> Any:
        """Class level attribute getter.

        Needed for operations like `Client.class_method()`.

        Args:
            name: The name of the attribute to access.

        Returns:
            The value of the attribute.
        """
        return getattr(Client, name)


class TheZenRemembers(metaclass=TheMetaZenRemembers):
    """The Class to create TheZenRemembers class.

    This a class that is used to create a proxy to the Client class.
    It memorizes the created objects and deletes them on `destroy`.
    """

    mem: ClassVar[Dict[bool, List[Tuple[str, Any]]]] = {False: [], True: []}
    interface: Union[Client, BaseZenStore]

    def __init__(self, interface: Optional[BaseZenStore] = None):
        """Initialize TheZenRemembers.

        Args:
            interface: The interface to use.
        """
        if interface is None:
            self.interface = Client()
            self.zen_store = TheZenRemembers(self.interface.zen_store)
            self.is_store = False
        else:
            self.interface = interface
            self.is_store = True

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the client.

        Args:
            name: The name of the attribute to access.

        Returns:
            The value of the attribute.
        """
        val = getattr(self.interface, name)
        if callable(val) and (
            name.startswith("create_") or name.startswith("get_or_create_")
        ):
            return TheZenRemembers.memory(val, name, self.is_store)
        return val

    def __call__(self, *args: Any, **kwargs: Any) -> "TheZenRemembers":
        """Simulate Client(), but return self.

        Args:
            args: The positional arguments.
            kwargs: The keyword arguments.

        Returns:
            self
        """
        return self

    @staticmethod
    def memory(
        func: Callable[..., Any], name: str, is_store: bool
    ) -> Callable[..., Any]:
        """Decorator to remember which objects have been created.

        Args:
            func: The function to decorate.
            name: The name of the function.
            is_store: Whether the function is a ZenStore function.

        Returns:
            The decorated function.
        """

        def run_and_memorize(*args: Any, **kwargs: Any) -> Any:
            """Inner function to remember which objects have been created.

            Args:
                args: The positional arguments.
                kwargs: The keyword arguments.

            Returns:
                The result of the function call.
            """
            ret = func(*args, **kwargs)
            if not isinstance(ret, MagicMock):
                TheZenRemembers.mem[is_store].append((name, ret))
            return ret

        return run_and_memorize

    def destroy(self) -> None:
        """Deletes all remembered objects."""
        from zenml.client_lazy_loader import _original_args_specs

        def get_delete_name(create_name: str) -> str:
            if name.startswith("get_or_create_"):
                return create_name.replace("get_or_create_", "delete_")
            return create_name.replace("create_", "delete_")

        def parse_annotations(
            spec: inspect.FullArgSpec, response_model: Any
        ) -> Dict[str, Any]:
            annotations = spec.annotations
            kwargs = {}
            for arg_name, arg_type in annotations.items():
                if arg_name == "return":
                    continue
                if arg_type == Union[str, UUID] or arg_type == UUID:
                    kwargs[arg_name] = getattr(response_model, "id", None)
                    continue
                if arg_type.__args__ and arg_type.__args__[-1] != type(None):
                    kwargs[arg_name] = getattr(response_model, arg_name, None)
            return kwargs

        while self.mem[True]:
            name, response_model = self.mem[True].pop()
            delete_name = get_delete_name(name)
            try:
                if func := getattr(
                    self.zen_store.interface, delete_name, None
                ):
                    func(
                        **parse_annotations(
                            inspect.getfullargspec(func), response_model
                        )
                    )
                else:
                    print("Could not find ZenStore method: ", delete_name)
            except KeyError:
                print(f"__STORE__.{name}: {response_model}")
                # the resource was deleted in the test session already
                pass

        while self.mem[False]:
            name, response_model = self.mem[False].pop()
            delete_name = get_delete_name(name)
            try:
                if func := getattr(self.interface, delete_name, None):
                    func(
                        **parse_annotations(
                            _original_args_specs[name], response_model
                        )
                    )
                else:
                    print("Could not find Client method: ", delete_name)
            except KeyError:
                print(f"__CLIENT__.{name}: {response_model}")
                # the resource was deleted in the test session already
                pass


@contextmanager
def self_cleaning_client_session() -> Generator[TheZenRemembers, None, None]:
    """Context manager to initialize and use a self cleaning ZenML client.

    This context manager creates a ZenML client with memory and cleans up
    resource created during the session.

    Raises:
        RuntimeError: If no default client is found.

    Yields:
        A clean ZenML client.
    """
    memory_client = TheZenRemembers()

    try:
        yield memory_client
    finally:
        memory_client.destroy()


@contextmanager
def clean_default_client_session(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Client, None, None]:
    """Context manager to initialize and use a clean local default ZenML client.

    This context manager creates a clean ZenML client with its own global
    configuration and local database.

    Args:
        tmp_path_factory: A pytest fixture that provides a temporary directory.

    Yields:
        A clean ZenML client.
    """
    # save the current global configuration and client singleton instances
    # to restore them later, then reset them
    orig_cwd = os.getcwd()
    original_config = GlobalConfiguration.get_instance()
    original_client = Client.get_instance()
    orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)

    GlobalConfiguration._reset_instance()
    Client._reset_instance()

    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("pytest-clean-client")
    os.chdir(tmp_path)

    os.environ[ENV_ZENML_CONFIG_PATH] = str(tmp_path / "zenml")
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

    # initialize the global config client and store at the new path
    gc = GlobalConfiguration()
    gc.analytics_opt_in = False
    client = Client()
    _ = client.zen_store

    logging.info(f"Tests are running in clean environment: {tmp_path}")

    yield client

    # restore the global configuration path
    if orig_config_path:
        os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
    else:
        del os.environ[ENV_ZENML_CONFIG_PATH]

    # restore the global configuration and the client
    GlobalConfiguration._reset_instance(original_config)
    Client._reset_instance(original_client)

    # remove all traces, and change working directory back to base path
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
