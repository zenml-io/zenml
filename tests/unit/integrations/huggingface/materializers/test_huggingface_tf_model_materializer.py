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

from transformers import TFAutoModelForSequenceClassification, TFPreTrainedModel

from zenml.integrations.huggingface.materializers.huggingface_tf_model_materializer import (
    HFTFModelMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step


def test_huggingface_tf_pretrained_model_materializer(clean_repo):
    """Tests whether the steps work for the Huggingface Tensorflow Pretrained Model materializer."""

    @step
    def read_model() -> TFPreTrainedModel:
        """Reads and materializes a Huggingface Tensorflow Pretrained Model."""
        return TFAutoModelForSequenceClassification.from_pretrained(
            "bert-base-cased", num_labels=5
        )

    @pipeline
    def test_pipeline(read_model) -> None:
        """Tests the Huggingface Tensorflow Pretrained Model materializer."""
        read_model()

    with does_not_raise():
        test_pipeline(
            read_model=read_model().with_return_materializers(
                HFTFModelMaterializer
            )
        ).run()

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    model = last_run.steps[-1].output.read()
    assert isinstance(model, TFPreTrainedModel)
