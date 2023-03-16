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
from pipelines import (
    pytorch_inference_pipeline,
    pytorch_training_deployment_pipeline,
)
from rich import print
from steps.deployment_trigger import (
    DeploymentTriggerParameters,
    deployment_trigger,
)
from steps.prediction_service_loader import (
    PredictionServiceLoaderStepParameters,
    prediction_service_loader,
)
from steps.pytorch_steps import (
    PytorchDataLoaderParameters,
    PyTorchInferenceProcessorStepParameters,
    PytorchTrainerParameters,
    pytorch_data_loader,
    pytorch_evaluator,
    pytorch_inference_processor,
    pytorch_model_deployer,
    pytorch_predictor,
    pytorch_trainer,
)

from zenml.integrations.kserve.model_deployers import KServeModelDeployer
from zenml.integrations.kserve.services import KServeDeploymentService

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
    "--batch-size",
    default=4,
    help="Number of epochs for training (tensorflow hyperparam)",
)
@click.option(
    "--epochs",
    default=3,
    help="Number of epochs for training (tensorflow hyperparam)",
)
@click.option(
    "--lr",
    default=0.01,
    help="Learning rate for training (tensorflow hyperparam, default: 0.003)",
)
@click.option(
    "--momentum",
    default=0.5,
    help="Learning rate for training (tensorflow hyperparam, default: 0.003)",
)
@click.option(
    "--min-accuracy",
    default=0.80,
    help="Minimum accuracy required to deploy the model (default: 0.92)",
)
def main(
    config: str,
    batch_size: int,
    epochs: int,
    lr: float,
    momentum: float,
    min_accuracy: float,
):
    """Run the KServe-Pytorch example training/deployment or inference pipeline.

    Example usage:

        python run.py --deploy --min-accuracy 0.80

    """
    deploy = config == DEPLOY or config == DEPLOY_AND_PREDICT
    predict = config == PREDICT or config == DEPLOY_AND_PREDICT

    model_name = "mnist-pytorch"
    deployment_pipeline_name = "pytorch_training_deployment_pipeline"
    deployer_step_name = "deployer"

    model_deployer = KServeModelDeployer.get_active_model_deployer()

    if deploy:
        # Initialize and run a continuous deployment pipeline run
        pytorch_training_deployment_pipeline(
            data_loader=pytorch_data_loader(
                PytorchDataLoaderParameters(
                    train_batch_size=batch_size, test_batch_size=batch_size
                )
            ),
            trainer=pytorch_trainer(
                PytorchTrainerParameters(
                    epochs=epochs, lr=lr, momentum=momentum
                )
            ),
            evaluator=pytorch_evaluator(),
            deployment_trigger=deployment_trigger(
                params=DeploymentTriggerParameters(
                    min_accuracy=min_accuracy,
                )
            ),
            deployer=pytorch_model_deployer,
        ).run()

    img_url: str = "https://raw.githubusercontent.com/kserve/kserve/master/docs/samples/v1beta1/torchserve/v1/imgconv/1.png"

    if predict:
        # Initialize an inference pipeline run
        pytorch_inference_pipeline(
            pytorch_inference_processor=pytorch_inference_processor(
                PyTorchInferenceProcessorStepParameters(
                    img_url=img_url,
                ),
            ),
            prediction_service_loader=prediction_service_loader(
                PredictionServiceLoaderStepParameters(
                    pipeline_name=deployment_pipeline_name,
                    step_name=deployer_step_name,
                    model_name=model_name,
                )
            ),
            predictor=pytorch_predictor(),
        ).run()

    services = model_deployer.find_model_server(
        pipeline_name=deployment_pipeline_name,
        pipeline_step_name=deployer_step_name,
        model_name=model_name,
    )
    if services:
        service = cast(KServeDeploymentService, services[0])
        if service.is_running:
            print(
                f"The KServe prediction server is running remotely as a Kubernetes "
                f"service and accepts inference requests at:\n"
                f"    {service.prediction_url}\n"
                f"    With the hostname: {service.prediction_hostname}.\n"
                f"To stop the service, run "
                f"[italic green]`zenml model-deployer models delete "
                f"{str(service.uuid)}`[/italic green]."
            )
        elif service.is_failed:
            print(
                f"The KServe prediction server is in a failed state:\n"
                f" Last state: '{service.status.state.value}'\n"
                f" Last error: '{service.status.last_error}'"
            )

    else:
        print(
            "No KServe prediction server is currently running. The deployment "
            "pipeline must run first to train a model and deploy it. Execute "
            "the same command with the `--deploy` argument to deploy a model."
        )


if __name__ == "__main__":
    main()
