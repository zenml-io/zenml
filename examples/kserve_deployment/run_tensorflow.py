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
from typing import cast

import click
from pipelines import (
    tensorflow_inference_pipeline,
    tensorflow_training_deployment_pipeline,
)
from steps.deployment_trigger import (
    DeploymentTriggerParameters,
    deployment_trigger,
)
from steps.prediction_service_loader import (
    PredictionServiceLoaderStepParameters,
    prediction_service_loader,
)
from steps.tensorflow_steps import (
    TensorflowTrainerParameters,
    importer_mnist,
    kserve_tensorflow_deployer,
    normalizer,
    tf_evaluator,
    tf_predict_preprocessor,
    tf_predictor,
    tf_trainer,
)

from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (
    KServeModelDeployer,
)
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentService,
)

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
    "--min-accuracy",
    default=0.92,
    help="Minimum accuracy required to deploy the model (default: 0.92)",
)
def main(
    config: str,
    epochs: int,
    lr: float,
    min_accuracy: float,
):
    """Run the Seldon example continuous deployment or inference pipeline.
    Example usage:
        `python run.py --deploy --predict --model-flavor tensorflow \
             --min-accuracy 0.80`
    """
    deploy = config == DEPLOY or config == DEPLOY_AND_PREDICT
    predict = config == PREDICT or config == DEPLOY_AND_PREDICT

    model_name = "mnist-tensorflow"
    deployment_pipeline_name = "tensorflow_training_deployment_pipeline"
    deployer_step_name = "model_deployer"

    model_deployer = KServeModelDeployer.get_active_model_deployer()

    if deploy:
        # Initialize a continuous deployment pipeline run
        deployment = tensorflow_training_deployment_pipeline(
            importer=importer_mnist(),
            normalizer=normalizer(),
            trainer=tf_trainer(
                TensorflowTrainerParameters(epochs=epochs, lr=lr)
            ),
            evaluator=tf_evaluator(),
            deployment_trigger=deployment_trigger(
                params=DeploymentTriggerParameters(
                    min_accuracy=min_accuracy,
                )
            ),
            model_deployer=kserve_tensorflow_deployer,
        )

        deployment.run()

    if predict:
        # Initialize an inference pipeline run
        inference = tensorflow_inference_pipeline(
            predict_preprocessor=tf_predict_preprocessor(),
            prediction_service_loader=prediction_service_loader(
                PredictionServiceLoaderStepParameters(
                    pipeline_name=deployment_pipeline_name,
                    step_name=deployer_step_name,
                    model_name=model_name,
                )
            ),
            predictor=tf_predictor(),
        )

        inference.run()

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
