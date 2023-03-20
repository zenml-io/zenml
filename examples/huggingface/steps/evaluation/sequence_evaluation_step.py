#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import tensorflow as tf
from datasets import DatasetDict
from steps.configuration import HuggingfaceParameters
from transformers import (
    DataCollatorWithPadding,
    PreTrainedTokenizerBase,
    TFPreTrainedModel,
)

from zenml.steps import step


@step
def sequence_evaluator(
    params: HuggingfaceParameters,
    model: TFPreTrainedModel,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> float:
    """Evaluate trained model on validation set."""
    # Needs to recompile because we are reloading model for evaluation
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metrics = ["accuracy"]
    model.compile(
        optimizer=tf.keras.optimizers.Adam(), loss=loss_fn, metrics=metrics
    )

    # Convert into tf dataset format
    validation_set = tokenized_datasets["test"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=False,
        batch_size=params.batch_size,
        collate_fn=DataCollatorWithPadding(tokenizer, return_tensors="tf"),
    )

    # Calculate loss

    if params.dummy_run:
        test_loss, test_acc = model.evaluate(
            validation_set.take(10), verbose=1
        )
    else:
        test_loss, test_acc = model.evaluate(validation_set, verbose=1)
    return test_loss
