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
from materializers.pillow_image_materializer import PillowImageMaterializer
from pipelines import inference_pipeline, training_pipeline
from steps.convert_annotations_step import convert_annotations
from steps.deployment_triggers import deployment_trigger
from steps.get_labeled_data import get_labeled_data_step
from steps.get_or_create_dataset import get_or_create_the_dataset
from steps.load_image_data_step import LoadImageDataConfig, load_image_data
from steps.model_deployers import model_deployer
from steps.prediction_steps import (
    PredictionServiceLoaderConfig,
    prediction_service_loader,
    predictor,
)
from steps.pytorch_trainer import (
    PytorchModelTrainerConfig,
    pytorch_model_trainer,
)
from steps.sync_new_data_to_label_studio import (
    azure_data_sync,
    gcs_data_sync,
    s3_data_sync,
)


@click.command()
@click.argument("cloud_platform")
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
def main(cloud_platform, pipeline, rerun):
    """Simple CLI interface for annotation example."""
    if cloud_platform == "azure":
        sync_function = azure_data_sync
    elif cloud_platform == "gcp":
        sync_function = gcs_data_sync
    elif cloud_platform == "aws":
        sync_function = s3_data_sync
    elif cloud_platform not in ["azure", "gcp", "aws"]:
        raise ValueError(
            f"Cloud platform '{cloud_platform}' is not supported for this example."
        )

    if pipeline == "train":
        training_pipeline(
            get_or_create_dataset=get_or_create_the_dataset,
            get_labeled_data=get_labeled_data_step,
            convert_annotations=convert_annotations(),
            model_trainer=pytorch_model_trainer(PytorchModelTrainerConfig()),
            deployment_trigger=deployment_trigger(),
            model_deployer=model_deployer,
        ).run()
    elif pipeline == "inference":
        inference_pipeline(
            get_or_create_dataset=get_or_create_the_dataset,
            inference_data_loader=load_image_data(
                config=LoadImageDataConfig(
                    dir_name="batch_2" if rerun else "batch_1"
                )
            ).with_return_materializers({"images": PillowImageMaterializer}),
            prediction_service_loader=prediction_service_loader(
                PredictionServiceLoaderConfig()
            ),
            predictor=predictor(),
            data_syncer=sync_function,
        ).run()


if __name__ == "__main__":
    main()
