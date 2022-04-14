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
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict
from transformers import (
    AutoTokenizer,
    DataCollatorWithPadding,
    PreTrainedTokenizerBase,
    TFAutoModelForSequenceClassification,
    TFPreTrainedModel,
    create_optimizer,
)

from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, step


class SequenceClassificationConfig(BaseStepConfig):
    """Config for the sequence-classification"""

    pretrained_model = "distilbert-base-uncased"
    batch_size = 16
    dataset_name = "imdb"
    epochs = 3
    max_seq_length = 128
    init_lr = 2e-5
    weight_decay_rate = 0.01
    text_column = "text"
    label_column = "label"


@step
def data_importer(
    config: SequenceClassificationConfig,
) -> DatasetDict:
    """Load imdb dataset using huggingface datasets"""
    datasets = load_dataset(config.dataset_name)
    print("Sample Example :", datasets["train"][0])
    return datasets


@step
def load_tokenizer(
    config: SequenceClassificationConfig,
) -> PreTrainedTokenizerBase:
    """Load pretrained tokenizer"""
    tokenizer = AutoTokenizer.from_pretrained(config.pretrained_model)
    return tokenizer


@step
def tokenization(
    config: SequenceClassificationConfig,
    tokenizer: PreTrainedTokenizerBase,
    datasets: DatasetDict,
) -> DatasetDict:
    """Tokenize dataset into tokens and then convert into encoded ids"""

    def preprocess_function(examples):
        result = tokenizer(
            examples[config.text_column],
            max_length=config.max_seq_length,
            truncation=True,
        )
        result["label"] = examples[config.label_column]
        return result

    tokenized_datasets = datasets.map(preprocess_function, batched=True)
    return tokenized_datasets


@step
def trainer(
    config: SequenceClassificationConfig,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> TFPreTrainedModel:
    """Build and Train token classification model"""

    # Get label list
    label_list = tokenized_datasets["train"].unique("label")

    # Load pre-trained model from huggingface hub
    model = TFAutoModelForSequenceClassification.from_pretrained(
        config.pretrained_model, num_labels=len(label_list)
    )

    # Prepare optimizer
    num_train_steps = (
        len(tokenized_datasets["train"]) // config.batch_size
    ) * config.epochs
    optimizer, _ = create_optimizer(
        init_lr=config.init_lr,
        num_train_steps=num_train_steps,
        weight_decay_rate=config.weight_decay_rate,
        num_warmup_steps=num_train_steps * 0.1,
    )

    # Compile model
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metrics = ["accuracy"]
    model.compile(optimizer=optimizer, loss=loss_fn, metrics=metrics)

    # Convert tokenized datasets into tf dataset
    train_set = tokenized_datasets["train"].to_tf_dataset(
        columns=["attention_mask", "input_ids"],
        shuffle=True,
        batch_size=config.batch_size,
        collate_fn=DataCollatorWithPadding(tokenizer, return_tensors="tf"),
        label_cols="label",
    )

    model.fit(train_set, epochs=config.epochs)
    return model


@step
def evaluator(
    config: SequenceClassificationConfig,
    model: TFPreTrainedModel,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> float:
    """Evaluate trained model on validation set"""
    # Needs to recompile because we are reloading model for evaluation
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metrics = ["accuracy"]
    model.compile(
        optimizer=tf.keras.optimizers.Adam(), loss=loss_fn, metrics=metrics
    )

    # Convert into tf dataset format
    validation_set = tokenized_datasets["test"].to_tf_dataset(
        columns=["attention_mask", "input_ids"],
        shuffle=False,
        batch_size=config.batch_size,
        collate_fn=DataCollatorWithPadding(tokenizer, return_tensors="tf"),
        label_cols="label",
    )

    # Calculate loss
    test_loss, test_acc = model.evaluate(validation_set, verbose=1)
    return test_loss


@pipeline
def seq_classifier_train_eval_pipeline(
    importer, load_tokenizer, tokenization, trainer, evaluator
):
    """Train and Evaluation pipeline"""
    datasets = importer()
    tokenizer = load_tokenizer()
    tokenized_datasets = tokenization(tokenizer=tokenizer, datasets=datasets)
    model = trainer(tokenized_datasets=tokenized_datasets, tokenizer=tokenizer)
    evaluator(
        model=model, tokenized_datasets=tokenized_datasets, tokenizer=tokenizer
    )
