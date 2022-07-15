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


from zenml.logger import get_logger
from zenml.pipelines import pipeline

logger = get_logger(__name__)


@pipeline
def training_pipeline(
    get_or_create_dataset,
    get_labeled_data,
    convert_annotations,
    model_trainer
) -> None:
    dataset_name = get_or_create_dataset()
    labeled_data = get_labeled_data(dataset_name)
    training_images, training_annotations = convert_annotations(labeled_data)
    model_trainer(training_images, training_annotations)
