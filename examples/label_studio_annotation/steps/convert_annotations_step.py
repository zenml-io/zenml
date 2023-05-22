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
from typing import Any, Dict, List

from zenml import step
from zenml.logger import get_logger
from zenml.steps import Output

logger = get_logger(__name__)


@step
def convert_annotations(
    label_studio_annotations: List[Dict[Any, Any]]
) -> Output(image_urls=List, image_labels=List):
    """Converts the annotation from Label Studio to a dictionary."""
    image_urls, labels = [], []
    for annotation in label_studio_annotations:
        image_url = annotation["data"]["image"]
        label = annotation["annotations"][0]["result"][0]["value"]["choices"][
            0
        ]
        image_urls.append(image_url)
        labels.append(label)
    return image_urls, labels
