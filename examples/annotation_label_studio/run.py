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
from materializers import FastaiLearnerMaterializer
from pipelines import inference_pipeline, training_pipeline
from steps import (
    azure_data_sync,
    convert_annotations_step,
    deployment_trigger,
    fastai_model_trainer,
    get_labeled_data_step,
    get_or_create_the_dataset,
    model_deployer,
    model_loader,
    prediction_service_loader,
    predictor,
)


@click.command()
@click.option(
    "--train",
    "pipeline",
    flag_value="train",
    default=True,
    help="Run the training pipeline.",
)
@click.option(
    "--inference",
    "pipeline",
    flag_value="inference",
    help="Run the inference pipeline.",
)
def main(pipeline):
    """Simple CLI interface for annotation example."""
    if pipeline == "train":
        training_pipeline(
            get_or_create_dataset=get_or_create_the_dataset,
            get_labeled_data=get_labeled_data_step,
            convert_annotations=convert_annotations_step,
            model_trainer=fastai_model_trainer().with_return_materializers(
                FastaiLearnerMaterializer
            ),  # TODO
            deployment_trigger=deployment_trigger(),
            model_deployer=model_deployer,
        ).run()
    elif pipeline == "inference":
        inference_pipeline(
            inference_data_loader=None  # TODO
            prediction_service_loader=prediction_service_loader(),  # TODO
            predictor=predictor(),  # TODO
            data_sync=azure_data_sync,
        ).run()


if __name__ == "__main__":
    main()
