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
from pipelines import inference_pipeline, training_pipeline
from steps.configuration import HuggingfaceParameters
from steps.convert_annotations_step import convert_annotations
from steps.deployment_triggers import deployment_trigger
from steps.get_labeled_data import get_labeled_data_step
from steps.get_or_create_dataset import get_or_create_the_dataset
from steps.load_image_data_step import LoadTextDataParameters, load_text_data
from steps.model_deployers import model_deployer
from steps.prediction_steps import (
    PredictionServiceLoaderParameters,
    prediction_service_loader,
    predictor,
)
from steps.pytorch_trainer import (
    pytorch_model_trainer,
)
from steps.sync_new_data_to_label_studio import data_sync


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
@click.option(
    "--rerun",
    is_flag=True,
    default=False,
)
def main(pipeline, rerun):
    """Simple CLI interface for annotation example."""
    if pipeline == "train":
        training_pipeline(
            get_or_create_dataset=get_or_create_the_dataset,
            get_labeled_data=get_labeled_data_step,
            convert_annotations=convert_annotations(),
            model_trainer=pytorch_model_trainer(HuggingfaceParameters()),
            deployment_trigger=deployment_trigger(),
            model_deployer=model_deployer,
        ).run()
    elif pipeline == "inference":
        inference_pipeline(
            get_or_create_dataset=get_or_create_the_dataset,
            inference_data_loader=load_text_data(
                params=LoadTextDataParameters(
                    dir_name="batch_2" if rerun else "batch_1"
                )
            ),
            prediction_service_loader=prediction_service_loader(
                PredictionServiceLoaderParameters()
            ),
            predictor=predictor(),
            data_syncer=data_sync,
        ).run()


if __name__ == "__main__":
    main()
