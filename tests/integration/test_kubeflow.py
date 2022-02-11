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
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import ExecutionStatus
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
from zenml.repository import Repository
from zenml.stack import Stack

QUICKSTART = "quickstart"
NOT_SO_QUICKSTART = "not_so_quickstart"
CACHING = "caching"
DRIFT_DETECTION = "drift_detection"
MLFLOW = "mlflow_tracking"
CUSTOM_MATERIALIZER = "custom_materializer"
WHYLOGS = "whylogs"
FETCH_HISTORICAL_RUNS = "fetch_historical_runs"
KUBEFLOW = "kubeflow"


def _wait_for_kubeflow_pipeline():
    import time

    import kfp
    from kubernetes import config as k8s_config

    # wait for 10 seconds so the run can start
    time.sleep(10)

    k8s_config.load_config()
    client = kfp.Client()
    latest_run_id = client.list_runs().runs[-1].id
    client.wait_for_run_completion(run_id=latest_run_id, timeout=300)


@pytest.fixture(scope="module")
def shared_kubeflow_repo(base_repo, tmp_path_factory, module_mocker):
    # patch the ui daemon as forking doesn't work well with pytest
    module_mocker.patch(
        "zenml.integrations.kubeflow.orchestrators.local_deployment_utils.start_kfp_ui_daemon"
    )

    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)
    Repository.initialize(root=tmp_path)
    repo = Repository(root=tmp_path)

    repo.original_cwd = base_repo.original_cwd

    orchestrator = KubeflowOrchestrator(
        name="local_kubeflow_orchestrator",
        custom_docker_base_image_name="localhost:5000/base-image:latest",
    )
    metadata_store = repo.active_stack.metadata_store.copy(
        update={"name": "local_kubeflow_metadata_store"}
    )
    artifact_store = repo.active_stack.artifact_store.copy(
        update={"name": "local_kubeflow_artifact_store"}
    )
    container_registry = BaseContainerRegistry(
        name="local_registry", uri="localhost:5000"
    )
    kubeflow_stack = Stack(
        name="local_kubeflow_stack",
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
        container_registry=container_registry,
    )
    repo.register_stack(kubeflow_stack)
    repo.activate_stack(kubeflow_stack.name)
    kubeflow_stack.provision()

    subprocess.check_call(
        ["docker", "push", "localhost:5000/base-image:latest"]
    )

    yield repo

    os.chdir(str(base_repo.root))
    shutil.rmtree(tmp_path)


@pytest.fixture
def clean_kubeflow_repo(shared_kubeflow_repo, clean_repo):
    kubeflow_stack = shared_kubeflow_repo.active_stack
    clean_repo.register_stack(kubeflow_stack)
    clean_repo.activate_stack(kubeflow_stack.name)

    # Delete the artifact store of previous tests
    if os.path.exists(kubeflow_stack.artifact_store.path):
        shutil.rmtree(kubeflow_stack.artifact_store.path)

    yield clean_repo


@pytest.fixture
def examples_dir(clean_kubeflow_repo):
    # TODO [high]: tests should store zenml artifacts in a new temp directory
    examples_path = Path(clean_kubeflow_repo.root) / "zenml_examples"
    source_path = Path(clean_kubeflow_repo.original_cwd) / "examples"
    shutil.copytree(source_path, examples_path)
    shutil.copytree(
        clean_kubeflow_repo.root / ".zen", examples_path / "kubeflow" / ".zen"
    )
    yield examples_path


def example_runner(examples_dir):
    """Get the executable that runs examples.

    By default returns the path to an executable .sh file in the
    repository, but can also prefix that with the path to a shell
    / interpreter when the file is not executable on its own. The
    latter option is needed for windows compatibility.
    """
    return (
        [os.environ[SHELL_EXECUTABLE]] if SHELL_EXECUTABLE in os.environ else []
    ) + [str(examples_dir / EXAMPLES_RUN_SCRIPT)]


def test_run_kubeflow(examples_dir: Path):
    """Testing the functionality of the kubeflow example

    Args:
        examples_dir: Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / KUBEFLOW, name=KUBEFLOW)
    local_example.run_example(
        example_runner(examples_dir), force=False, prevent_stack_setup=True
    )
    _wait_for_kubeflow_pipeline()

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mnist_pipeline"

    pipeline_run = pipeline.runs[-1]

    assert pipeline_run.status == ExecutionStatus.COMPLETED

    for step in pipeline_run.steps:
        assert step.status == ExecutionStatus.COMPLETED
