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

import sys

import pytest
from transformers import TFAutoModelForSequenceClassification

from tests.unit.test_general import _test_materializer
from zenml.integrations.huggingface.materializers.huggingface_tf_model_materializer import (
    HFTFModelMaterializer,
)


@pytest.mark.skipif(
    sys.version_info.minor == 12,
    reason="The tensorflow integrations is not yet supported on 3.12.",
)
def test_huggingface_tf_pretrained_model_materializer(clean_client):
    """Tests whether the steps work for the Huggingface Tensorflow Pretrained Model materializer."""
    model = _test_materializer(
        step_output=TFAutoModelForSequenceClassification.from_pretrained(
            "bert-base-cased", num_labels=5
        ),
        materializer_class=HFTFModelMaterializer,
        expected_metadata_size=4,
    )

    assert model.config.max_position_embeddings == 512
    assert model.config.model_type == "bert"
