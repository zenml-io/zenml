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

from materializers import FastaiLearnerMaterializer, PillowImageMaterializer
from pipelines import continuous_training_pipeline
from steps import (
    batch_inference,
    convert_annotation,
    load_image_data,
    model_loader,
)

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
    ["cat", "dog"]
)

label_studio_registration_config = LabelStudioDatasetRegistrationConfig(
    label_config=label_config,
    dataset_name="catvsdog",
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


get_or_create_the_dataset = get_or_create_dataset(
    label_studio_registration_config
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


def is_cat(x):
    # NEEDED FOR FASTAI MODEL IMPORT (when / if we use it)
    # return labels[x] == "cat"
    return True


if __name__ == "__main__":
    ct_pipeline = continuous_training_pipeline(
        get_or_create_the_dataset,
        get_labeled_data(),
        convert_annotation(),
        model_loader().with_return_materializers(FastaiLearnerMaterializer),
        # fine_tuning_step().with_return_materializers(
        #     FastaiLearnerMaterializer
        # ),
        load_image_data().with_return_materializers(
            {"images": PillowImageMaterializer}
        ),
        batch_inference(),
        azure_data_sync,
    )

    ct_pipeline.run()
