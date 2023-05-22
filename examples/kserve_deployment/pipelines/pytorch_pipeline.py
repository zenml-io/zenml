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
from zenml.config import DockerSettings
from zenml.integrations.constants import KSERVE, PYTORCH

docker_settings = DockerSettings(
    requirements=["torchvision"], required_integrations=[KSERVE, PYTORCH]
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def pytorch_training_deployment_pipeline(
    data_loader,
    trainer,
    evaluator,
    deployment_trigger,
    deployer,
):
    train_loader, test_loader = data_loader()
    model = trainer(train_loader)
    accuracy = evaluator(model=model, test_loader=test_loader)
    deployment_decision = deployment_trigger(accuracy=accuracy)
    deployer(deployment_decision, model)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def pytorch_inference_pipeline(
    pytorch_inference_processor,
    prediction_service_loader,
    predictor,
):
    # Link all the steps artifacts together
    inference_request = pytorch_inference_processor()
    model_deployment_service = prediction_service_loader()
    predictor(model_deployment_service, inference_request)
