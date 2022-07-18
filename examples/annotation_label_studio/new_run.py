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
from pipelines import training_pipeline
from steps import convert_annotations, fastai_model_trainer

from zenml.integrations.label_studio.label_config_generators import (
    generate_image_classification_label_config,
)
from zenml.integrations.label_studio.steps import (
    LabelStudioDatasetRegistrationConfig,
    LabelStudioDatasetSyncConfig,
    get_labeled_data,
    get_or_create_dataset,
    sync_new_data_to_label_studio,
)
from zenml.logger import get_logger

IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

logger = get_logger(__name__)


label_config, label_config_type = generate_image_classification_label_config(
    ["aria", "not_aria"]
)

label_studio_registration_config = LabelStudioDatasetRegistrationConfig(
    label_config=label_config,
    dataset_name="aria_detector",
)

get_or_create_the_dataset = get_or_create_dataset(
    label_studio_registration_config
)


zenml_azure_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="azure",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
)

zenml_gcs_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="gcs",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
)

zenml_s3_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="s3",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
    s3_region_name="eu-west-1",  # change this to your closest region
)


azure_data_sync = sync_new_data_to_label_studio(
    config=zenml_azure_artifact_store_sync_config,
)

gcs_data_sync = sync_new_data_to_label_studio(
    config=zenml_gcs_artifact_store_sync_config,
)

s3_data_sync = sync_new_data_to_label_studio(
    config=zenml_s3_artifact_store_sync_config,
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
            get_labeled_data=get_labeled_data(),
            convert_annotations=convert_annotations(),
            model_trainer=fastai_model_trainer().with_return_materializers(
                FastaiLearnerMaterializer
            ),
        ).run()
    elif pipeline == "inference":
        # inference_pipeline()
        raise NotImplementedError("Inference pipeline not implemented yet.")


if __name__ == "__main__":
    main()
