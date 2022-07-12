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


def is_cat(x):
    # NEEDED FOR FASTAI MODEL IMPORT (when / if we use it)
    # return labels[x] == "cat"
    return True


@pipeline
def continuous_training_pipeline(
    get_or_create_dataset,
    get_labeled_data,
    annotation_converter,
    get_model,
    # fine_tuner,
    images_loader,
    batch_inference,
    data_syncer,
) -> None:
    dataset_name = get_or_create_dataset()
    # TODO: get any *fresh* labeled data for our dataset
    # Use an option to pass in filters (or use the 'meta' field)
    new_annotations = get_labeled_data(dataset_name)

    training_images, training_annotations = annotation_converter(
        new_annotations
    )
    model = get_model()
    # new_model = fine_tuner(model, training_images, training_annotations)
    # model = compare_and_validate(model, new_model)

    # TODO: POSSIBLY SPLIT PIPELINE HERE INTO NEW PIPELINE??
    # uploads some new local images to the ZenML artifact store
    new_images_dict, new_images_uri = images_loader()

    preds = batch_inference(new_images_dict, model)

    # sync from zenml artifact store to label studio (azure blob storage)
    data_syncer(
        uri=new_images_uri, dataset_name=dataset_name, predictions=preds
    )
