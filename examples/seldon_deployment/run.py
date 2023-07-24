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
from pipelines.deployment_pipeline import continuous_deployment_pipeline
from pipelines.inference_pipeline import inference_pipeline
from rich import print

from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
    SeldonModelDeployer,
)
from zenml.integrations.seldon.services import SeldonDeploymentService

DEPLOY = "deploy"
PREDICT = "predict"
DEPLOY_AND_PREDICT = "deploy_and_predict"


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Choice([DEPLOY, PREDICT, DEPLOY_AND_PREDICT]),
    default="deploy_and_predict",
    help="Optionally you can choose to only run the deployment "
    "pipeline to train and deploy a model (`deploy`), or to "
    "only run a prediction against the deployed model "
    "(`predict`). By default both will be run "
    "(`deploy_and_predict`).",
)
@click.option(
    "--model-flavor",
    default="tensorflow",
    type=click.Choice(["tensorflow", "sklearn"]),
    help="Flavor of model being trained",
)
@click.option(
    "--epochs",
    default=5,
    help="Number of epochs for training (tensorflow hyperparam)",
)
@click.option(
    "--lr",
    default=0.003,
    help="Learning rate for training (tensorflow hyperparam, default: 0.003)",
)
@click.option(
    "--solver",
    default="saga",
    type=click.Choice(["newton-cg", "lbfgs", "liblinear", "sag", "saga"]),
    help="Algorithm to use in the optimization problem "
    "(sklearn hyperparam, default: saga)",
)
@click.option(
    "--penalty",
    default="l1",
    type=click.Choice(["l1", "l2", "elasticnet", "none"]),
    help="Regularization (penalty) norm (sklearn hyperparam, default: l1)",
)
@click.option(
    "--penalty-strength",
    default=1.0,
    type=float,
    help="Regularization (penalty) strength (sklearn hyperparam, default: 1.0)",
)
@click.option(
    "--toleration",
    default=0.1,
    type=float,
    help="Tolerance for stopping criteria (sklearn hyperparam, default: 0.1)",
)
@click.option(
    "--min-accuracy",
    default=0.92,
    help="Minimum accuracy required to deploy the model (default: 0.92)",
)
def main(
    config: str,
    model_flavor: str,
    epochs: int,
    lr: float,
    solver: str,
    penalty: str,
    penalty_strength: float,
    toleration: float,
    min_accuracy: float,
):
    """Run the Seldon example continuous deployment or inference pipeline.

    Example usage:

        python run.py --config deploy_and_predict --model-flavor tensorflow \
             --min-accuracy 0.80

    """
    deploy = config == DEPLOY or config == DEPLOY_AND_PREDICT
    predict = config == PREDICT or config == DEPLOY_AND_PREDICT

    model_name = "mnist"
    deployment_pipeline_name = "continuous_deployment_pipeline"
    deployer_step_name = "seldon_model_deployer_step"

    if deploy:
        continuous_deployment_pipeline(
            model_name=model_name,
            model_flavor=model_flavor,
            epochs=epochs,
            lr=lr,
            solver=solver,
            penalty=penalty,
            penalty_strength=penalty_strength,
            toleration=toleration,
            min_accuracy=min_accuracy,
        )

    if predict:
        inference_pipeline(
            deployment_pipeline_name=deployment_pipeline_name,
            deployer_step_name=deployer_step_name,
            model_name=model_name,
            model_flavor=model_flavor,
        )

    model_deployer = SeldonModelDeployer.get_active_model_deployer()
    services = model_deployer.find_model_server(
        pipeline_name=deployment_pipeline_name,
        pipeline_step_name=deployer_step_name,
        model_name=model_name,
    )
    if services:
        service = cast(SeldonDeploymentService, services[0])
        if service.is_running:
            print(
                f"The Seldon prediction server is running remotely as a Kubernetes "
                f"service and accepts inference requests at:\n"
                f"    {service.prediction_url}\n"
                f"To stop the service, run "
                f"[italic green]`zenml model-deployer models delete "
                f"{str(service.uuid)}`[/italic green]."
            )
        elif service.is_failed:
            print(
                f"The Seldon prediction server is in a failed state:\n"
                f" Last state: '{service.status.state.value}'\n"
                f" Last error: '{service.status.last_error}'"
            )

    else:
        print(
            "No Seldon prediction server is currently running. The deployment "
            "pipeline must run first to train a model and deploy it. Execute "
            "the same command with the `--deploy` argument to deploy a model."
        )


if __name__ == "__main__":
    main()
