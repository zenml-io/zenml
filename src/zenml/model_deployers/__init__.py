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
"""Model deployers are stack components responsible for online model serving.

Online serving is the process of hosting and loading machine-learning models as
part of a managed web service and providing access to the models through an API
endpoint like HTTP or GRPC. Once deployed, you can send inference requests
to the model through the web service's API and receive fast, low-latency
responses.

Add a model deployer to your ZenML stack to be able to implement continuous
model deployment pipelines that train models and continuously deploy them to a
model prediction web service.

When present in a stack, the model deployer also acts as a registry for models
that are served with ZenML. You can use the model deployer to list all models
that are currently deployed for online inference or filtered according
to a particular pipeline run or step, or to suspend, resume or delete
an external model server managed through ZenML.
"""

from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployer,
    BaseModelDeployerFlavor,
)

__all__ = [
    "BaseModelDeployer",
    "BaseModelDeployerFlavor",
]
