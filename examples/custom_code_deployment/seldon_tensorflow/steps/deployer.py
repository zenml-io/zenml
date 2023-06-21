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

from zenml.integrations.seldon.seldon_client import SeldonResourceRequirements
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentConfig,
)
from zenml.integrations.seldon.steps.seldon_deployer import (
    seldon_custom_model_deployer_step,
)

seldon_tensorflow_custom_deployment = seldon_custom_model_deployer_step.with_options(
    parameters=dict(
        predict_function="seldon_tensorflow.steps.tf_custom_deploy_code.custom_predict",
        service_config=SeldonDeploymentConfig(
            model_name="seldon-tensorflow-custom-model",
            replicas=1,
            implementation="custom",
            resources=SeldonResourceRequirements(
                limits={"cpu": "200m", "memory": "250Mi"}
            ),
        ),
        timeout=240,
    )
)
