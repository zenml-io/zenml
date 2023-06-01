#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import cast

import click
from pipelines import continuous_deployment_pipeline, inference_pipeline
from rich import print

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services import MLFlowDeploymentService

DEPLOY = "deploy"
PREDICT = "predict"
DEPLOY_AND_PREDICT = "deploy_and_predict"


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Choice([DEPLOY, PREDICT, DEPLOY_AND_PREDICT]),
    default=DEPLOY_AND_PREDICT,
    help="Optionally you can choose to only run the deployment "
    "pipeline to train and deploy a model (`deploy`), or to "
    "only run a prediction against the deployed model "
    "(`predict`). By default both will be run "
    "(`deploy_and_predict`).",
)
@click.option("--epochs", default=5, help="Number of epochs for training")
@click.option("--lr", default=0.003, help="Learning rate for training")
@click.option(
    "--min-accuracy",
    default=0.92,
    help="Minimum accuracy required to deploy the model",
)
def main(config: str, epochs: int, lr: float, min_accuracy: float):
    """Run the MLflow example pipeline."""
    # get the MLflow model deployer stack component
    mlflow_model_deployer_component = (
        MLFlowModelDeployer.get_active_model_deployer()
    )
    deploy = config == DEPLOY or config == DEPLOY_AND_PREDICT
    predict = config == PREDICT or config == DEPLOY_AND_PREDICT

    if deploy:
        # Initialize a continuous deployment pipeline run
        continuous_deployment_pipeline(
            epochs=epochs,
            lr=lr,
            min_accuracy=min_accuracy,
            workers=3,
            timeout=60,
        )

        trainer_step = continuous_deployment_pipeline.get_runs()[0].get_step(
            "tf_trainer"
        )
        tracking_uri = trainer_step.metadata[
            METADATA_EXPERIMENT_TRACKER_URL
        ].value
        print(
            "You can run:\n "
            f"[italic green]    mlflow ui --backend-store-uri '{tracking_uri}"
            "[/italic green]\n ...to inspect your experiment runs within the MLflow"
            " UI.\nYou can find your runs tracked within the "
            "`mlflow_example_pipeline` experiment. There you'll also be able to "
            "compare two or more runs.\n\n"
        )

    if predict:
        # Initialize an inference pipeline run
        inference_pipeline(
            pipeline_name="continuous_deployment_pipeline",
            pipeline_step_name="mlflow_model_deployer_step",
        )

    # fetch existing services with same pipeline name, step name and model name
    existing_services = mlflow_model_deployer_component.find_model_server(
        pipeline_name="continuous_deployment_pipeline",
        pipeline_step_name="mlflow_model_deployer_step",
        model_name="model",
    )

    if existing_services:
        service = cast(MLFlowDeploymentService, existing_services[0])
        if service.is_running:
            print(
                f"The MLflow prediction server is running locally as a daemon "
                f"process service and accepts inference requests at:\n"
                f"    {service.prediction_url}\n"
                f"To stop the service, run "
                f"[italic green]`zenml model-deployer models delete "
                f"{str(service.uuid)}`[/italic green]."
            )
        elif service.is_failed:
            print(
                f"The MLflow prediction server is in a failed state:\n"
                f" Last state: '{service.status.state.value}'\n"
                f" Last error: '{service.status.last_error}'"
            )
    else:
        print(
            "No MLflow prediction server is currently running. The deployment "
            "pipeline must run first to train a model and deploy it. Execute "
            "the same command with the `--deploy` argument to deploy a model."
        )


if __name__ == "__main__":
    main()
