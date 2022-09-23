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


from zenml.config import DockerSettings
from zenml.integrations.constants import SELDON, TENSORFLOW
from zenml.pipelines import pipeline

docker_settings = DockerSettings(
    requirements=["Pillow"], required_integrations=[SELDON, TENSORFLOW]
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def tensorflow_custom_code_pipeline(
    data_loader,
    trainer,
    evaluator,
    deployment_trigger,
    deployer,
):
    x_train, y_train, x_test, y_test = data_loader()
    model = trainer(x_train=x_train, y_train=y_train)
    accuracy = evaluator(x_test=x_test, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(accuracy=accuracy)
    deployer(deployment_decision, model)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def tensorflow_inference_pipeline(
    inference_image_loader,
    prediction_service_loader,
    predictor,
):
    # Link all the steps artifacts together
    inference_request = inference_image_loader()
    model_deployment_service = prediction_service_loader()
    predictor(model_deployment_service, inference_request)
