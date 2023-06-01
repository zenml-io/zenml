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

from zenml.integrations.bentoml.steps import (
    BentoMLBuilderParameters,
    bento_builder_step,
)

bento_builder = bento_builder_step(
    params=BentoMLBuilderParameters(
        model_name=MODEL_NAME,
        model_type="pytorch",
        service="service.py:svc",
        labels={
            "framework": "pytorch",
            "dataset": "mnist",
            "zenml_version": "0.40.1",
        },
        exclude=["data"],
        python={
            "packages": ["zenml", "torch", "torchvision"],
        },
    )
)
