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
    TFAutoModelForSequenceClassification,
    TFPreTrainedModel,
    create_optimizer,
)

from zenml.steps import step


@step
def sequence_trainer(
    params: HuggingfaceParameters,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> TFPreTrainedModel:
    """Build and Train token classification model."""
    # Get label list
    label_list = tokenized_datasets["train"].unique("label")

    # Load pre-trained model from huggingface hub
    model = TFAutoModelForSequenceClassification.from_pretrained(
        params.pretrained_model, num_labels=len(label_list)
    )

    num_train_steps = (
        len(tokenized_datasets["train"]) // params.batch_size
    ) * params.epochs

    # Prepare optimizer
    optimizer, _ = create_optimizer(
        init_lr=params.init_lr,
        num_train_steps=num_train_steps,
        weight_decay_rate=params.weight_decay_rate,
        num_warmup_steps=num_train_steps * 0.1,
    )

    # Compile model
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metrics = ["accuracy"]
    model.compile(optimizer=optimizer, loss=loss_fn, metrics=metrics)

    # Convert tokenized datasets into tf dataset
    train_set = tokenized_datasets["train"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=True,
        batch_size=params.batch_size,
        collate_fn=DataCollatorWithPadding(tokenizer, return_tensors="tf"),
    )

    if params.dummy_run:
        model.fit(train_set.take(10), epochs=params.epochs)
    else:
        model.fit(train_set, epochs=params.epochs)
    return model
