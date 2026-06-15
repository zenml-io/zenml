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
"""Tests for the Hugging Face TensorFlow model materializer."""

import sys

import pytest

from tests.unit.test_general import _test_materializer


@pytest.mark.skipif(
    sys.version_info.minor in (12, 13, 14),
    reason="The tensorflow integrations is not yet supported on 3.12, 3.13 or 3.14.",
)
def test_huggingface_tf_pretrained_model_materializer(clean_client):
    """Tests whether the steps work for the Huggingface Tensorflow Pretrained Model materializer."""
    import tensorflow as tf
    from transformers import BertConfig, TFBertForSequenceClassification

    from zenml.integrations.huggingface.materializers.huggingface_tf_model_materializer import (
        HFTFModelMaterializer,
    )

    model = TFBertForSequenceClassification(
        BertConfig(
            hidden_size=32,
            intermediate_size=37,
            num_attention_heads=4,
            num_hidden_layers=1,
            num_labels=5,
            vocab_size=100,
        )
    )
    model(input_ids=tf.constant([[1, 2]]))

    model = _test_materializer(
        step_output=model,
        materializer_class=HFTFModelMaterializer,
        expected_metadata_size=4,
    )

    assert model.config.max_position_embeddings == 512
    assert model.config.model_type == "bert"
