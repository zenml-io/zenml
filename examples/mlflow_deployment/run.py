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
import click
from pipeline import (
    DeploymentTriggerConfig,
    MLFlowDeploymentLoaderStepConfig,
    TrainerConfig,
    continuous_deployment_pipeline,
    deployment_trigger,
    dynamic_importer,
    importer_mnist,
    inference_pipeline,
    model_deployer,
    normalizer,
    prediction_service_loader,
    predictor,
    tf_evaluator,
    tf_trainer,
)
from rich import print

from zenml.integrations.mlflow.mlflow_environment import global_mlflow_env
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.steps import MLFlowDeployerConfig


@click.command()
@click.option("--epochs", default=5, help="Number of epochs for training")
@click.option("--lr", default=0.003, help="Learning rate for training")
@click.option(
    "--min-accuracy",
    default=0.92,
    help="Minimum accuracy required to deploy the model",
)
@click.option(
    "--stop-service",
    is_flag=True,
    default=False,
    help="Stop the prediction service when done",
)
def main(epochs: int, lr: float, min_accuracy: float, stop_service: bool):
    """Run the MLflow example pipeline"""

    # get the MLflow model deployer stack component
    mlflow_model_deployer_component = (
        MLFlowModelDeployer.get_active_model_deployer()
    )

    if stop_service:
        services = mlflow_model_deployer_component.find_model_server(
            pipeline_name="continuous_deployment_pipeline",
            pipeline_step_name="model_deployer",
            model_name="model",
        )
        if services[0]:
            services[0].stop(timeout=10)
        return

    # Initialize a continuous deployment pipeline run
    deployment = continuous_deployment_pipeline(
        importer=importer_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(config=TrainerConfig(epochs=epochs, lr=lr)),
        evaluator=tf_evaluator(),
        deployment_trigger=deployment_trigger(
            config=DeploymentTriggerConfig(
                min_accuracy=min_accuracy,
            )
        ),
        model_deployer=model_deployer(
            config=MLFlowDeployerConfig(workers=3, timeout=10)
        ),
    )

    deployment.run()

    # Initialize an inference pipeline run
    inference = inference_pipeline(
        dynamic_importer=dynamic_importer(),
        prediction_service_loader=prediction_service_loader(
            MLFlowDeploymentLoaderStepConfig(
                pipeline_name="continuous_deployment_pipeline",
                pipeline_step_name="model_deployer",
            )
        ),
        predictor=predictor(),
    )

    inference.run()

    with global_mlflow_env() as mlflow_env:
        print(
            "You can run:\n "
            f"[italic green]    mlflow ui --backend-store-uri {mlflow_env.tracking_uri}[/italic green]\n"
            "...to inspect your experiment runs within the MLflow UI.\n"
            "You can find your runs tracked within the `mlflow_example_pipeline`"
            "experiment. There you'll also be able to compare two or more runs.\n\n"
        )

    # fetch existing services with same pipeline name, step name and model name
    existing_services = mlflow_model_deployer_component.find_model_server(
        pipeline_name="continuous_deployment_pipeline",
        pipeline_step_name="model_deployer",
        model_name="model",
    )

    if existing_services[0]:
        print(
            f"The MLflow prediction server is running locally as a daemon process "
            f"and accepts inference requests at:\n"
            f"    {existing_services[0].prediction_uri}\n"
            f"To stop the service, re-run the same command and supply the "
            f"`--stop-service` argument."
        )


if __name__ == "__main__":
    main()
