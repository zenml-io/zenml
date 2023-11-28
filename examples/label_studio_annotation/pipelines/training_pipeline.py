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


from steps.convert_annotations_step import convert_annotations
from steps.get_or_create_dataset import get_or_create_the_dataset
from steps.pytorch_trainer import (
    pytorch_model_trainer,
)

from zenml import pipeline
from zenml.integrations.label_studio.steps.label_studio_standard_steps import (
    get_labeled_data,
)


@pipeline(enable_cache=False)
def training_pipeline():
    dataset_name = get_or_create_the_dataset()
    labeled_data = get_labeled_data(dataset_name)
    training_images, training_annotations = convert_annotations(labeled_data)
    pytorch_model_trainer(training_images, training_annotations)
