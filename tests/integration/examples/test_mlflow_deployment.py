#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


from sys import platform

import pytest

from tests.integration.examples.utils import run_example
from zenml.client import Client
from zenml.enums import ExecutionStatus


@pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="It hangs forever now. Need to investigate.",  # TODO: investigate this
)
def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the mlflow_deployment example."""
    with run_example(
        request=request,
        name="mlflow",
        example_args=["--type", "deployment"],
        pipelines={
            "mlflow_train_deploy_pipeline": (1, 5),
            "mlflow_deployment_inference_pipeline": (1, 4),
        },
    ):
        import mlflow
        from mlflow.tracking import MlflowClient

        from zenml.integrations.mlflow.experiment_trackers import (
            MLFlowExperimentTracker,
        )
        from zenml.integrations.mlflow.services import (
            MLFlowDeploymentService,
        )

        deployment_run = (
            Client().get_pipeline("mlflow_train_deploy_pipeline").last_run
        )
        assert deployment_run.status == ExecutionStatus.COMPLETED

        experiment_tracker = Client().active_stack.experiment_tracker
        assert isinstance(experiment_tracker, MLFlowExperimentTracker)
        experiment_tracker.configure_mlflow()

        # fetch the MLflow experiment created for the deployment run
        mlflow_experiment = mlflow.get_experiment_by_name(
            "mlflow_train_deploy_pipeline"
        )

        assert mlflow_experiment is not None

        # fetch the MLflow run created for the deployment run
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

        service = deployment_run.steps[
            "mlflow_model_deployer_step"
        ].output.load()
        assert isinstance(service, MLFlowDeploymentService)

        if service.is_running:
            service.stop(timeout=180)
