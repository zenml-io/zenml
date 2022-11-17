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
import click
from constants import MODEL_NAME, PIPELINE_NAME, PIPELINE_STEP_NAME
from pipelines.inference_fashion_mnist import inference_fashion_mnist
from pipelines.training_fashion_mnist import training_fashion_mnist
from steps.bento_builder import bento_builder
from steps.deployer import bentoml_model_deployer
from steps.deployment_trigger_step import (
    DeploymentTriggerParameters,
    deployment_trigger,
)
from steps.evaluators import evaluator
from steps.importers import importer_mnist
from steps.inference_loader import inference_loader
from steps.prediction_service_loader import (
    PredictionServiceLoaderStepParameters,
    bentoml_prediction_service_loader,
)
from steps.predictor import predictor
from steps.trainers import trainer

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
def main(
    config: str,
):
    deploy = config == DEPLOY or config == DEPLOY_AND_PREDICT
    predict = config == PREDICT or config == DEPLOY_AND_PREDICT

    if deploy:
        training_fashion_mnist(
            importer=importer_mnist(),
            trainer=trainer(),
            evaluator=evaluator(),
            deployment_trigger=deployment_trigger(
                params=DeploymentTriggerParameters(
                    min_accuracy=0.80,
                )
            ),
            bento_builder=bento_builder,
            deployer=bentoml_model_deployer,
        ).run()
    if predict:
        inference_fashion_mnist(
            inference_loader=inference_loader(),
            prediction_service_loader=bentoml_prediction_service_loader(
                params=PredictionServiceLoaderStepParameters(
                    model_name=MODEL_NAME,
                    pipeline_name=PIPELINE_NAME,
                    step_name=PIPELINE_STEP_NAME,
                )
            ),
            predictor=predictor(),
        ).run()


if __name__ == "__main__":
    main()
