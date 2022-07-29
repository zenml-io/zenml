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

import pytest
from typing import List
from hypothesis import given
from hypothesis.strategies import lists, text


from zenml.integrations.label_studio.label_config_generators import (
    generate_basic_object_detection_bounding_boxes_label_config,
    generate_image_classification_label_config,
)


@given(label_list=lists(text(min_size=1), min_size=1))
def test_image_classification_label_config_generator(label_list: List[str]):
    label_config = generate_image_classification_label_config(label_list)
    assert label_config is not None


def test_config_generator_raises_with_empty_list():
    with pytest.raises(ValueError):
        generate_image_classification_label_config([])

    with pytest.raises(ValueError):
        generate_basic_object_detection_bounding_boxes_label_config([])
