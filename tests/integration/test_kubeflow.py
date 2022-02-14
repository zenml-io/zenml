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
from collections import namedtuple
from pathlib import Path

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import ExecutionStatus
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
from zenml.repository import Repository
from zenml.stack import Stack


def generate_basic_validation_function(pipeline_name: str):
    def _validation_function(repository: Repository):
        pipeline = repository.get_pipeline(pipeline_name)
        assert pipeline
        run = pipeline.runs[-1]
        assert run.status == ExecutionStatus.COMPLETED

    return _validation_function


def not_so_quickstart_example_validation(repository: Repository):
    pipeline = repository.get_pipeline("mnist_pipeline")
    assert pipeline

    for run in pipeline.runs[-3:]:
        assert run.status == ExecutionStatus.COMPLETED


def caching_example_validation(repository: Repository):
    pipeline = repository.get_pipeline("mnist_pipeline")
    assert pipeline

    first_run, second_run = pipeline.runs[-2:]

    # Both runs should be completed
    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED

    # The first run should not have any cached steps
    for step in first_run.steps:
        assert not step.is_cached

    # The second run should have two cached steps (chronologically first 2)
    assert second_run.steps[0].is_cached
    assert second_run.steps[1].is_cached
    assert not second_run.steps[2].is_cached
    assert not second_run.steps[3].is_cached


ExampleIntegrationTestConfiguration = namedtuple(
    "ExampleIntegrationTestConfiguration", ["name", "validation_function"]
)
examples = [
    # ExampleIntegrationTestConfiguration(
    #     name="quickstart",
    #     validation_function=generate_basic_validation_function(
    #         pipeline_name="mnist_pipeline"
    #     ),
    # ),
    # ExampleIntegrationTestConfiguration(
    #     name="not_so_quickstart", validation_function=not_so_quickstart_example_validation
    # ),
    # ExampleIntegrationTestConfiguration(
    #     name="caching", validation_function=caching_example_validation
    # ),
    ExampleIntegrationTestConfiguration(
        name="custom_materializer",
        validation_function=generate_basic_validation_function(
            pipeline_name="pipe"
        ),
    ),
    # ExampleIntegrationTestConfiguration(
    #     name="fetch_historical_runs",
    #     validation_function=generate_basic_validation_function(
    #         pipeline_name="mnist_pipeline"
    #     ),
    # ),
    ExampleIntegrationTestConfiguration(
        name="kubeflow",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline"
        ),
    ),
]


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
        custom_docker_base_image_name="zenml-base-image:latest",
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


@pytest.mark.parametrize("example", examples)
def test_run_example_on_kfp(
    example: ExampleIntegrationTestConfiguration, examples_dir: Path
):
    local_example = LocalExample(examples_dir / example.name, name=example.name)
    # copy the shared kubeflow .zen directory
    shutil.copytree(examples_dir.parent / ".zen", local_example.path / ".zen")
    local_example.run_example(
        example_runner(examples_dir), force=False, prevent_stack_setup=True
    )
    _wait_for_kubeflow_pipeline()
    example.validation_function(Repository(root=local_example.path))


# def test_run_kubeflow(examples_dir: Path):
#     """Testing the functionality of the kubeflow example
#
#     Args:
#         examples_dir: Temporary folder containing all examples including the run_examples
#         bash script.
#     """
#     local_example = LocalExample(examples_dir / KUBEFLOW, name=KUBEFLOW)
#     shutil.copytree(examples_dir.parent / ".zen", local_example.path / ".zen")
#     local_example.run_example(
#         example_runner(examples_dir), force=False, prevent_stack_setup=True
#     )
#     _wait_for_kubeflow_pipeline()
#
#     # Verify the example run was successful
#     repo = Repository(local_example.path)
#     pipeline = repo.get_pipelines()[0]
#     assert pipeline.name == "mnist_pipeline"
#
#     pipeline_run = pipeline.runs[-1]
#
#     assert pipeline_run.status == ExecutionStatus.COMPLETED
#
#     for step in pipeline_run.steps:
#         assert step.status == ExecutionStatus.COMPLETED
#
#
# def test_run_custom_materializer(examples_dir: Path):
#     """Testing the functionality of the custom materializer example.
#
#     Args:
#         examples_dir: Temporary folder containing all examples including the
#                       run_examples bash script.
#     """
#     local_example = LocalExample(
#         examples_dir / CUSTOM_MATERIALIZER, name=CUSTOM_MATERIALIZER
#     )
#     shutil.copytree(examples_dir.parent / ".zen", local_example.path / ".zen")
#     local_example.run_example(
#         example_runner(examples_dir), force=False, prevent_stack_setup=True
#     )
#     _wait_for_kubeflow_pipeline()
#
#     # Verify the example run was successful
#     repo = Repository(local_example.path)
#     pipeline = repo.get_pipelines()[0]
#     first_run = pipeline.runs[-1]
#
#     # Both runs should be completed
#     assert first_run.status == ExecutionStatus.COMPLETED


# def test_run_mlflow(examples_dir: Path):
#     """Testing the functionality of the quickstart example
#
#     Args:
#         examples_dir: Temporary folder containing all examples including the run_examples
#         bash script.
#     """
#     local_example = LocalExample(examples_dir / MLFLOW, name=MLFLOW)
#     shutil.copytree(examples_dir.parent / ".zen", local_example.path / ".zen")
#     local_example.run_example(
#         example_runner(examples_dir), force=False, prevent_stack_setup=True
#     )
#     _wait_for_kubeflow_pipeline()
#
#     # Verify the example run was successful
#     repo = Repository(local_example.path)
#     pipeline = repo.get_pipelines()[0]
#     assert pipeline.name == "mlflow_example_pipeline"
#
#     first_run = pipeline.runs[-2]
#     second_run = pipeline.runs[-1]
#
#     # Both runs should be completed
#     assert first_run.status == ExecutionStatus.COMPLETED
#     assert second_run.status == ExecutionStatus.COMPLETED
#
#     for step in first_run.steps:
#         assert step.status == ExecutionStatus.COMPLETED
#     for step in second_run.steps:
#         assert step.status == ExecutionStatus.COMPLETED
#
#     import mlflow
#     from mlflow.tracking import MlflowClient
#
#     from zenml.integrations.mlflow.mlflow_environment import MLFlowEnvironment
#
#     # Create and activate the global MLflow environment
#     MLFlowEnvironment(local_example.path).activate()
#
#     # fetch the MLflow experiment created for the pipeline runs
#     mlflow_experiment = mlflow.get_experiment_by_name(pipeline.name)
#     assert mlflow_experiment is not None
#
#     # fetch all MLflow runs created for the pipeline
#     mlflow_runs = mlflow.search_runs(
#         experiment_ids=[mlflow_experiment.experiment_id], output_format="list"
#     )
#     assert len(mlflow_runs) == 2
#
#     # fetch the MLflow run created for the first pipeline run
#     mlflow_runs = mlflow.search_runs(
#         experiment_ids=[mlflow_experiment.experiment_id],
#         filter_string=f'tags.mlflow.runName = "{first_run.name}"',
#         output_format="list",
#     )
#     assert len(mlflow_runs) == 1
#     first_mlflow_run = mlflow_runs[0]
#
#     # fetch the MLflow run created for the second pipeline run
#     mlflow_runs = mlflow.search_runs(
#         experiment_ids=[mlflow_experiment.experiment_id],
#         filter_string=f'tags.mlflow.runName = "{second_run.name}"',
#         output_format="list",
#     )
#     assert len(mlflow_runs) == 1
#     second_mlflow_run = mlflow_runs[0]
#
#     client = MlflowClient()
#     # fetch the MLflow artifacts logged during the first pipeline run
#     artifacts = client.list_artifacts(first_mlflow_run.info.run_id)
#     assert len(artifacts) == 3
#
#     # fetch the MLflow artifacts logged during the second pipeline run
#     artifacts = client.list_artifacts(second_mlflow_run.info.run_id)
#     assert len(artifacts) == 3
