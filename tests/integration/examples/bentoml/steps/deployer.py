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

from constants import MODEL_NAME

from zenml.integrations.bentoml.steps import bentoml_model_deployer_step

bentoml_model_deployer = bentoml_model_deployer_step.with_options(
    parameters=dict(
        model_name=MODEL_NAME,  # Name of the model
        port=3000,  # Port to be used by the http server
        production=False,  # Deploy the model in production mode
        timeout=1000,
        deployment_type="local",  # change to "local" to run locally
    )
)
