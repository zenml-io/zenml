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

import platform

import pytest

from tests.integration.examples.utils import run_example
from zenml.client import Client
from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL


@pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="It hangs forever now. Need to investigate.",  # TODO: investigate this
)
def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the airflow_orchestration example."""
    import mlflow
    from mlflow.tracking import MlflowClient

    from zenml.integrations.mlflow.experiment_trackers import (
        MLFlowExperimentTracker,
    )

    with run_example(
        request=request,
        name="mlflow",
        example_args=["--type", "tracking"],
        pipelines={"mlflow_tracking_pipeline": (1, 4)},
        timeout_limit=750,
    ) as runs:
        client = Client()
        pipeline = client.get_pipeline("mlflow_tracking_pipeline")
        assert pipeline

        run = runs["mlflow_tracking_pipeline"][0]

        # activate the stack set up and used by the example

        experiment_tracker = client.active_stack.experiment_tracker
        assert isinstance(experiment_tracker, MLFlowExperimentTracker)
        experiment_tracker.configure_mlflow()

        # fetch the MLflow experiment created for the pipeline runs
        mlflow_experiment = mlflow.get_experiment_by_name(pipeline.name)
        assert mlflow_experiment is not None

        # fetch the MLflow run created for the first pipeline run
        mlflow_runs = mlflow.search_runs(
            experiment_ids=[mlflow_experiment.experiment_id],
            filter_string=f'tags.mlflow.runName = "{run.name}"',
            output_format="list",
        )
        assert len(mlflow_runs) == 1
        first_mlflow_run = mlflow_runs[0]

        client = MlflowClient()
        # fetch the MLflow artifacts logged during the first pipeline run
        artifacts = client.list_artifacts(first_mlflow_run.info.run_id)
        assert len(artifacts) == 3

        # ensure that tracking_url is set in the step metadata
        trainer_step = run.steps["trainer"]
        tracking_url = trainer_step.run_metadata.get(
            METADATA_EXPERIMENT_TRACKER_URL
        )
        assert tracking_url is not None
