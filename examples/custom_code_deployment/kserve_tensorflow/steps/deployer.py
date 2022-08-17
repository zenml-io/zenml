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

from zenml.integrations.kserve.services import KServeDeploymentConfig
from zenml.integrations.kserve.steps import (
    CustomDeployParameters,
    KServeDeployerStepConfig,
    kserve_custom_model_deployer_step,
)

kserve_tensorflow_custom_deployment = kserve_custom_model_deployer_step(
    config=KServeDeployerStepConfig(
        service_config=KServeDeploymentConfig(
            model_name="kserve-tensorflow-custom-model",
            replicas=1,
            predictor="custom",
            resources={"requests": {"cpu": "200m", "memory": "500m"}},
        ),
        timeout=240,
        custom_deploy_parameters=CustomDeployParameters(
            predict_function="kserve_tensorflow.steps.tf_custom_deploy_code.custom_predict"
        ),
    )
)
