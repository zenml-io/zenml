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


from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def inference_pipeline(
    get_or_create_dataset,
    inference_data_loader,
    prediction_service_loader,
    predictor,
    data_syncer,
):
    dataset_name = get_or_create_dataset()
    new_images, new_images_uri = inference_data_loader()
    model_deployment_service = prediction_service_loader()
    preds = predictor(model_deployment_service, new_images)
    data_syncer(
        uri=new_images_uri, dataset_name=dataset_name, predictions=preds
    )
