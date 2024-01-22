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


from steps.common.importer import dynamic_importer, inference_image_loader
from steps.common.prediction_service_loader import prediction_service_loader
from steps.common.predictor import predictor
from steps.sklearn.preprocessor import sklearn_predict_preprocessor
from steps.tensorflow.preprocessor import tf_predict_preprocessor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import PYTORCH, SELDON, SKLEARN, TENSORFLOW

docker_settings = DockerSettings(
    requirements=["torchvision", "Pillow"],
    required_integrations=[SELDON, TENSORFLOW, SKLEARN, PYTORCH],
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def inference_pipeline(
    deployment_pipeline_name: str = "seldon_deployment_pipeline",
    custom_code: bool = False,
    model_name: str = "mnist",
    model_flavor: str = "sklearn",
):
    # Load and preprocess the data
    if custom_code:
        inference_data = inference_image_loader()
    else:
        inference_data = dynamic_importer()
        if model_flavor == "tensorflow":
            inference_data = tf_predict_preprocessor(inference_data)
        else:
            inference_data = sklearn_predict_preprocessor(inference_data)

    # Load the model deployment service
    if custom_code:
        deployer_step_name = ("seldon_custom_model_deployer_step",)
    else:
        deployer_step_name = ("seldon_model_deployer_step",)
    model_deployment_service = prediction_service_loader(
        pipeline_name=deployment_pipeline_name,
        step_name=deployer_step_name,
        model_name=model_name,
    )

    # Run the predictor
    predictor(model_deployment_service, inference_data)
