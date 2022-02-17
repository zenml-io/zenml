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
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Dict

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import ExecutionStatus
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator
from zenml.repository import Repository
from zenml.stack import Stack


def generate_basic_validation_function(
    pipeline_name: str, step_count: int, run_count: int = 1
):
    """Generates a basic example validation function.

    This function will make sure the runs of a specific pipeline succeeded by
    checking the run status as well as making sure all steps were executed.

    Args:
        pipeline_name: The name of the pipeline to verify.
        step_count: The amount of steps inside the pipeline.
        run_count: The amount of pipeline runs to verify.

    Raises:
        AssertionError: If the validation failed.
    """

    def _validation_function(repository: Repository):
        """Basic validation of pipeline runs inside the metadata store."""
        pipeline = repository.get_pipeline(pipeline_name)
        assert pipeline

        for run in pipeline.runs[-run_count:]:
            assert run.status == ExecutionStatus.COMPLETED
            assert len(run.steps) == step_count

    return _validation_function


def caching_example_validation(repository: Repository):
    """Validates the metadata store after running the caching example."""
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


def drift_detection_example_validation(repository: Repository):
    """Validates the metadata store after running the drift detection
    example."""
    pipeline = repository.get_pipeline("drift_detection_pipeline")
    assert pipeline

    run = pipeline.runs[-1]
    assert run.status == ExecutionStatus.COMPLETED

    # Final step should have output a data drift report
    drift_detection_step = run.get_step("drift_detector")
    output = drift_detection_step.outputs["profile"].read()
    assert isinstance(output, Dict)
    assert output.get("data_drift") is not None


def mlflow_tracking_example_validation(repository: Repository):
    """Validates the metadata store after running the mlflow tracking
    example."""
    pipeline = repository.get_pipeline("mlflow_example_pipeline")
    assert pipeline

    first_run, second_run = pipeline.runs[-2:]

    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED

    import mlflow
    from mlflow.tracking import MlflowClient

    from zenml.integrations.mlflow.mlflow_environment import MLFlowEnvironment

    # Create and activate the global MLflow environment
    MLFlowEnvironment(repo_root=repository.root).activate()

    # fetch the MLflow experiment created for the pipeline runs
    mlflow_experiment = mlflow.get_experiment_by_name(pipeline.name)
    assert mlflow_experiment is not None

    # fetch all MLflow runs created for the pipeline
    mlflow_runs = mlflow.search_runs(
        experiment_ids=[mlflow_experiment.experiment_id], output_format="list"
    )
    assert len(mlflow_runs) == 2

    # fetch the MLflow run created for the first pipeline run
    mlflow_runs = mlflow.search_runs(
        experiment_ids=[mlflow_experiment.experiment_id],
        filter_string=f'tags.mlflow.runName = "{first_run.name}"',
        output_format="list",
    )
    assert len(mlflow_runs) == 1
    first_mlflow_run = mlflow_runs[0]

    # fetch the MLflow run created for the second pipeline run
    mlflow_runs = mlflow.search_runs(
        experiment_ids=[mlflow_experiment.experiment_id],
        filter_string=f'tags.mlflow.runName = "{second_run.name}"',
        output_format="list",
    )
    assert len(mlflow_runs) == 1
    second_mlflow_run = mlflow_runs[0]

    client = MlflowClient()
    # fetch the MLflow artifacts logged during the first pipeline run
    artifacts = client.list_artifacts(first_mlflow_run.info.run_id)
    assert len(artifacts) == 3

    # fetch the MLflow artifacts logged during the second pipeline run
    artifacts = client.list_artifacts(second_mlflow_run.info.run_id)
    assert len(artifacts) == 3


def whylogs_example_validation(repository: Repository):
    """Validates the metadata store after running the whylogs example."""
    pipeline = repository.get_pipeline("data_profiling_pipeline")
    assert pipeline

    run = pipeline.runs[-1]
    assert run.status == ExecutionStatus.COMPLETED

    from whylogs import DatasetProfile

    profiles = [
        run.get_step("data_loader").outputs["profile"].read(),
        run.get_step("train_data_profiler").output.read(),
        run.get_step("test_data_profiler").output.read(),
    ]

    for profile in profiles:
        assert isinstance(profile, DatasetProfile)


ExampleIntegrationTestConfiguration = namedtuple(
    "ExampleIntegrationTestConfiguration", ["name", "validation_function"]
)
examples = [
    ExampleIntegrationTestConfiguration(
        name="quickstart",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="not_so_quickstart",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=4, run_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="caching", validation_function=caching_example_validation
    ),
    ExampleIntegrationTestConfiguration(
        name="custom_materializer",
        validation_function=generate_basic_validation_function(
            pipeline_name="pipe", step_count=2
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="fetch_historical_runs",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="kubeflow",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=4
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="drift_detection",
        validation_function=drift_detection_example_validation,
    ),
    ExampleIntegrationTestConfiguration(
        name="mlflow_tracking",
        validation_function=mlflow_tracking_example_validation,
    ),
    # TODO [HIGH]: Enable running the whylogs example on kubeflow
    # ExampleIntegrationTestConfiguration(
    #     name="whylogs", validation_function=whylogs_example_validation
    # ),
]


@pytest.fixture(scope="module")
def shared_kubeflow_repo(base_repo, tmp_path_factory, module_mocker):
    """Creates a repo with a locally provisioned kubeflow stack.

    As the resource provisioning for the local kubeflow deployment takes quite
    a while, this fixture has a module scope and will therefore only run once.

    **Note**: The fixture should not be used directly. Use the
    `clean_kubeflow_repo` fixture instead that builds on top of this and
    provides the  test with a clean working directory and artifact/metadata
    store.
    """
    # Patch the ui daemon as forking doesn't work well with pytest
    module_mocker.patch(
        "zenml.integrations.kubeflow.orchestrators.local_deployment_utils.start_kfp_ui_daemon"
    )

    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)
    Repository.initialize(root=tmp_path)
    repo = Repository(root=tmp_path)

    repo.original_cwd = base_repo.original_cwd

    # Register and activate the kubeflow stack
    orchestrator = KubeflowOrchestrator(
        name="local_kubeflow_orchestrator",
        custom_docker_base_image_name="zenml-base-image:latest",
        synchronous=True,
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

    # Provision resources for the kubeflow stack
    kubeflow_stack.provision()

    yield repo

    # Deprovision the resources after all tests in this module are finished
    kubeflow_stack.deprovision()
    os.chdir(str(base_repo.root))
    shutil.rmtree(tmp_path)


@pytest.fixture
def clean_kubeflow_repo(shared_kubeflow_repo, clean_repo):
    """Creates a clean repo with a provisioned local kubeflow stack."""
    # Copy the stack configuration from the shared kubeflow repo. At this point
    # the stack resources are already provisioned by the module-scoped fixture.
    kubeflow_stack = shared_kubeflow_repo.active_stack
    clean_repo.register_stack(kubeflow_stack)
    clean_repo.activate_stack(kubeflow_stack.name)

    # Delete the artifact store of previous tests
    if os.path.exists(kubeflow_stack.artifact_store.path):
        shutil.rmtree(kubeflow_stack.artifact_store.path)

    yield clean_repo


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


@pytest.mark.parametrize(
    "example_configuration",
    [pytest.param(example, id=example.name) for example in examples],
)
@pytest.mark.parametrize(
    "repo_fixture_name", ["clean_repo"]  # , "clean_kubeflow_repo"]
)
def test_run_example(
    example_configuration: ExampleIntegrationTestConfiguration,
    repo_fixture_name,
    request,
):
    """Runs the given examples and validates they ran correctly."""
    # run the fixture given by repo_fixture_name
    repo = request.getfixturevalue(repo_fixture_name)

    # Root directory of all checked out examples
    examples_directory = Path(repo.original_cwd) / "examples"

    # Copy all example files into the repository directory
    # this uses a distutil method as shutil.copytree only has a dirs_exist_ok
    # parameter only since python 3.8
    copy_tree(
        str(examples_directory / example_configuration.name), str(repo.root)
    )

    # Run the example
    example = LocalExample(name=example_configuration.name, path=repo.root)
    example.run_example(
        example_runner(examples_directory),
        force=True,
        prevent_stack_setup=True,
    )

    # Validate the result
    example_configuration.validation_function(repo)
