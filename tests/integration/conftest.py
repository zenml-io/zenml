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
import shutil
import threading
from typing import Any, Callable, Generator, Optional, TypeVar

import pytest
from pytest_mock import MockerFixture

from zenml.exceptions import StackExistsError
from zenml.repository import Repository
from zenml.stack import Stack

F = TypeVar("F", bound=Callable[..., Any])

ECR_REGISTRY_NAME = "715803424590.dkr.ecr.us-east-1.amazonaws.com"
S3_BUCKET_NAME = "s3://zenbytes-bucket"
KUBE_CONTEXT = "zenml-eks"


@pytest.fixture(scope="module")
def shared_kubeflow_profile(
    base_profile: Repository,
    module_mocker: MockerFixture,
) -> Generator[Repository, None, None]:
    """Creates and activates a locally provisioned kubeflow stack.

    As the resource provisioning for the local kubeflow deployment takes quite
    a while, this fixture has a module scope and will therefore only run once.

    **Note**: The fixture should not be used directly. Use the
    `clean_kubeflow_repo` fixture instead that builds on top of this and
    provides the test with a clean working directory and artifact/metadata
    store.

    Args:
        base_profile: The base ZenML repository for tests with a clean profile.
        module_mocker: Mocker fixture

    Yields:
        The input repository with a local kubeflow stack provisioned for the
        module active profile.
    """
    from zenml.container_registries import DefaultContainerRegistry
    from zenml.integrations.kubeflow.metadata_stores import (
        KubeflowMetadataStore,
    )
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
    from zenml.integrations.s3.artifact_stores import S3ArtifactStore

    def run_in_thread(
        daemon_function: F,
        *args: Any,
        pid_file: str,
        log_file: Optional[str] = None,
        working_directory: str = "/",
        **kwargs: Any
    ):
        # run the actual passed function in a daemon thread
        t = threading.Thread(target=daemon_function, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()

        # As we are creating a daemon thread instead of a real daemon process,
        #  no pid file is created, so we now need to pretend the pid file exists
        def fake_pid_file_exists(pid_file: str):
            return True

        module_mocker.patch(
            "zenml.utils.daemon.check_if_daemon_is_running",
            new=fake_pid_file_exists,
        )

    def return_false():
        return False

    module_mocker.patch("zenml.utils.daemon.run_as_daemon", new=run_in_thread)
    module_mocker.patch(
        "zenml.environment.Environment.in_notebook", new=return_false
    )

    # Register and activate the kubeflow stack
    orchestrator = KubeflowOrchestrator(
        name="eks_orchestrator",
        custom_docker_base_image_name="test-base-image:latest",
        synchronous=True,
        kubernetes_context=KUBE_CONTEXT,
        skip_ui_daemon_provisioning=True,
    )

    metadata_store = KubeflowMetadataStore(
        name="kubeflow_metadata_store",
    )
    artifact_store = S3ArtifactStore(name="s3_store", path=S3_BUCKET_NAME)
    container_registry = DefaultContainerRegistry(
        name="ecr_registry", uri=ECR_REGISTRY_NAME
    )
    try:
        kubeflow_stack = Stack(
            name="aws_test_kubeflow_stack",
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
            container_registry=container_registry,
        )
    except StackExistsError:
        pass

    base_profile.register_stack(kubeflow_stack)
    base_profile.activate_stack(kubeflow_stack.name)

    # Provision resources for the kubeflow stack

    kubeflow_stack.provision()
    kubeflow_stack.resume()

    yield base_profile

    # Deprovision the resources after all tests in this module are finished
    kubeflow_stack.deprovision()


def cleanup_active_profile() -> None:
    """Clean up all previously stored information from the artifact store and
    metadata store in the current stack.
    """

    kubeflow_stack = Repository().active_stack

    # Delete the artifact store and metadata store of previous tests
    if os.path.exists(kubeflow_stack.artifact_store.path):
        shutil.rmtree(
            kubeflow_stack.artifact_store.path, onerror=fix_permissions
        )


def fix_permissions(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    This is especially helpful on Windows systems, where permission errors
    are frequent.

    Usage : ``shutil.rmtree(path, onerror=fix_permissions)``
    """
    import subprocess
    subprocess.call(f'rm -rf {path}', shell=True)


@pytest.fixture
def clean_kubeflow_profile(
    shared_kubeflow_profile: Repository,
) -> Generator[Repository, None, None]:
    """Creates a clean environment with a provisioned local kubeflow stack.

    This fixture reuses the stack configuration from the shared kubeflow
    profile. The stack resources are already provisioned by the module-scoped
    fixture and all that's done here is to clean up all previously stored
    information from the artifact store and metadata store.

    Args:
        shared_kubeflow_profile: A repository with a provisioned local kubeflow
            stack

    Yields:
        An empty repository with a provisioned local kubeflow stack.
    """
    cleanup_active_profile()

    yield shared_kubeflow_profile


@pytest.fixture
def clean_base_profile(
    base_profile: Repository,
) -> Generator[Repository, None, None]:
    """Creates a clean environment with an empty artifact store and metadata
    store out of the shared base profile.

    Args:
        base_profile: A repository with a provisioned profile shared by all
            tests in the current module.

    Yields:
        A repository with an empty artifact store and metadata store.
    """
    cleanup_active_profile()

    yield base_profile
