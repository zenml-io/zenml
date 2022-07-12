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
from typing import Dict, List

from fastai.learner import Learner

from zenml.logger import get_logger
from zenml.steps import step

logger = get_logger(__name__)


@step(enable_cache=False)
def batch_inference(image_dict: Dict, model: Learner) -> List:
    """Execute batch inference on some images.

    Returns a list of predictions compatible with Label Studio.
    """
    # TODO: [HIGH] Actually implement the batch inference step
    # below are just dummy values
    return [
        {
            "filename": image_name,
            "result": [
                {
                    "value": {"choices": ["cat"]},
                    "from_name": "choice",
                    "to_name": "image",
                    "type": "choices",
                    "origin": "manual",
                },
            ],
        }
        for image_name in image_dict.keys()
    ]
