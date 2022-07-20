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
def inference_pipeline(
    get_or_create_dataset,
    images_loader,
    get_model,
    batch_inference,
    data_syncer,
) -> None:
    dataset_name = get_or_create_dataset()
    new_images_dict, new_images_uri = images_loader()
    model = get_model()
    preds = batch_inference(new_images_dict, model)
    data_syncer(
        uri=new_images_uri, dataset_name=dataset_name, predictions=preds
    )
