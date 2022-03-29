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
from typing import Dict

from zenml.enums import ExecutionStatus
from zenml.repository import Repository


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
    MLFlowEnvironment().activate()

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


def mlflow_deployment_example_validation(repository: Repository):
    """Validates the metadata store after running the MLflow deployment
    example."""

    # Verify the example run was successful
    deployment_pipeline = repository.get_pipeline(
        "continuous_deployment_pipeline"
    )
    assert deployment_pipeline is not None

    inference_pipeline = repository.get_pipeline("inference_pipeline")
    assert inference_pipeline is not None

    deployment_run = deployment_pipeline.runs[-1]

    # Run should be completed
    assert deployment_run.status == ExecutionStatus.COMPLETED

    for step in deployment_run.steps:
        assert step.status == ExecutionStatus.COMPLETED

    inference_run = inference_pipeline.runs[-1]

    # Run should be completed
    assert inference_run.status == ExecutionStatus.COMPLETED

    for step in inference_run.steps:
        assert step.status == ExecutionStatus.COMPLETED

    import mlflow
    from mlflow.tracking import MlflowClient

    from zenml.integrations.mlflow.mlflow_environment import MLFlowEnvironment

    # create and activate the global MLflow environment
    MLFlowEnvironment().activate()

    # fetch the MLflow experiment created for the pipeline runs
    mlflow_experiment = mlflow.get_experiment_by_name(deployment_pipeline.name)

    assert mlflow_experiment is not None

    # fetch all MLflow runs created for the pipeline
    mlflow_runs = mlflow.search_runs(
        experiment_ids=[mlflow_experiment.experiment_id], output_format="list"
    )
    assert len(mlflow_runs) == 1

    # fetch the MLflow run created for the pipeline run
    mlflow_runs = mlflow.search_runs(
        experiment_ids=[mlflow_experiment.experiment_id],
        filter_string=f'tags.mlflow.runName = "{deployment_run.name}"',
        output_format="list",
    )
    assert len(mlflow_runs) == 1
    mlflow_run = mlflow_runs[0]

    client = MlflowClient()
    # fetch the MLflow artifacts logged during the first pipeline run
    artifacts = client.list_artifacts(mlflow_run.info.run_id)
    assert len(artifacts) == 3

    from zenml.integrations.mlflow.services import MLFlowDeploymentService

    # the predictor step should have an MLflow deployment artifact as output
    service = deployment_run.get_step("model_deployer").output.read()

    assert isinstance(service, MLFlowDeploymentService)

    # the service should not be running (stopped by the example post_run hook)
    assert service.is_stopped


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
