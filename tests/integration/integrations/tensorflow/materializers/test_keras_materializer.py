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
from tensorflow import keras

from tests.unit.test_general import _test_materializer
from zenml.integrations.tensorflow.materializers.keras_materializer import (
    KerasMaterializer,
)


@pytest.mark.skipif(
    sys.version_info.minor >= 12,
    reason="The tensorflow integrations is not yet supported on 3.12.",
)
def test_tensorflow_keras_materializer(clean_client):
    """Tests whether the steps work for the TensorFlow Keras materializer."""
    inputs = keras.Input(shape=(32,))
    outputs = keras.layers.Dense(1)(inputs)
    model = keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="mean_squared_error")

    model = _test_materializer(
        step_output=model,
        materializer_class=KerasMaterializer,
        expected_metadata_size=4,
    )

    assert isinstance(model.optimizer, keras.optimizers.Adam)
    assert model.trainable
