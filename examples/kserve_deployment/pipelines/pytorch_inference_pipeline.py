#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from zenml.integrations.constants import KSERVE, PYTORCH, SKLEARN
from zenml.pipelines import pipeline


@pipeline(enable_cache=True, required_integrations=[KSERVE, PYTORCH, SKLEARN])
def pytorch_inference_pipeline(
    load_inference_image,
    prediction_service_loader,
    predictor,
):
    # Link all the steps artifacts together
    inference_request = load_inference_image()
    model_deployment_service = prediction_service_loader()
    predictor(model_deployment_service, inference_request)
