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
from contextlib import ExitStack as does_not_raise

from tensorflow import keras

from zenml.integrations.tensorflow.materializers.keras_materializer import (
    KerasMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step


def test_tensorflow_keras_materializer(clean_repo):
    """Tests whether the steps work for the TensorFlow Keras materializer."""

    @step
    def read_model() -> keras.Model:
        """Reads and materializes a Keras model."""
        inputs = keras.Input(shape=(32,))
        outputs = keras.layers.Dense(1)(inputs)
        model = keras.Model(inputs, outputs)
        model.compile(optimizer="adam", loss="mean_squared_error")
        return model

    @pipeline
    def test_pipeline(read_model) -> None:
        """Tests the PillowImageMaterializer."""
        read_model()

    with does_not_raise():
        test_pipeline(
            read_model=read_model().with_return_materializers(KerasMaterializer)
        ).run()

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    model = last_run.steps[-1].output.read()
    assert isinstance(model, keras.Model)
    assert isinstance(model.optimizer, keras.optimizers.Adam)
    assert model.trainable
