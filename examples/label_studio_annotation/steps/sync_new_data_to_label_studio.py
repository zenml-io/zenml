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
from zenml.integrations.label_studio.label_config_generators import (
    generate_image_classification_label_config,
)
from zenml.integrations.label_studio.steps import (
    LabelStudioDatasetSyncParameters,
    sync_new_data_to_label_studio,
)

IMAGE_REGEX_FILTER = ".*(jpe?g|png|JPE?G|PNG)"


_, label_config_type = generate_image_classification_label_config(
    ["aria", "not_aria"]
)


zenml_sync_params = LabelStudioDatasetSyncParameters(
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
)

data_sync = sync_new_data_to_label_studio.with_options(
    parameters={"params": zenml_sync_params},
)
