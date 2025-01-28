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


@pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="It hangs forever now. Need to investigate.",  # TODO: investigate this
)
def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the MLFlow Registry example."""

    import mlflow
    from mlflow.tracking import MlflowClient

    from zenml.integrations.mlflow.experiment_trackers import (
        MLFlowExperimentTracker,
    )
    from zenml.integrations.mlflow.model_registries import (
        MLFlowModelRegistry,
    )

    with run_example(
        request=request,
        name="mlflow",
        example_args=["--type", "registry"],
        pipelines={
            "mlflow_registry_training_pipeline": (1, 5),
            "mlflow_registry_inference_pipeline": (1, 4),
        },
    ) as runs:
        pipeline = Client().get_pipeline("mlflow_registry_training_pipeline")
        assert pipeline
        first_training_run = runs["mlflow_registry_training_pipeline"][0]

        # activate the stack set up and used by the example
        client = Client()
        experiment_tracker = client.active_stack.experiment_tracker
        assert isinstance(experiment_tracker, MLFlowExperimentTracker)
        experiment_tracker.configure_mlflow()
        model_registry = client.active_stack.model_registry
        assert isinstance(model_registry, MLFlowModelRegistry)

        # fetch the MLflow experiment created for the pipeline runs
        mlflow_experiment = mlflow.get_experiment_by_name(pipeline.name)
        assert mlflow_experiment is not None

        # fetch the MLflow run created for the pipeline run
        mlflow_runs = mlflow.search_runs(
            experiment_ids=[mlflow_experiment.experiment_id],
            filter_string=f'tags.mlflow.runName = "{first_training_run.name}"',
            output_format="list",
        )
        assert len(mlflow_runs) == 1
        first_mlflow_run = mlflow_runs[0]

        client = MlflowClient()
        # fetch the MLflow artifacts logged during the pipeline run
        artifacts = client.list_artifacts(first_mlflow_run.info.run_id)
        assert len(artifacts) == 3

        # fetch the MLflow registered model
        registered_model = model_registry.get_model(
            name="sklearn-mnist-model",
        )
        assert registered_model is not None

        # fetch the MLflow registered model version
        registered_model_version = model_registry.get_model_version(
            name="sklearn-mnist-model",
            version="1",
        )
        assert registered_model_version is not None
