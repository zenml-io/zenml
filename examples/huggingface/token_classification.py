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
    DataCollatorForTokenClassification,
    PreTrainedTokenizerBase,
    TFAutoModelForTokenClassification,
    TFPreTrainedModel,
    create_optimizer,
)

from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, step


class TokenClassificationConfig(BaseStepConfig):
    """Config for the token-classification"""

    pretrained_model = "distilbert-base-uncased"
    batch_size = 16
    dataset_name = "conll2003"
    label_all_tokens = True
    epochs = 3
    init_lr = 2e-5
    weight_decay_rate = 0.01
    text_column = "tokens"
    label_column = "ner_tags"


@step
def data_importer(
    config: TokenClassificationConfig,
) -> DatasetDict:
    """Load conll2003 using huggingface dataset"""
    datasets = load_dataset(config.dataset_name)
    print("Sample Example :", datasets["train"][0])
    return datasets


@step
def load_tokenizer(
    config: TokenClassificationConfig,
) -> PreTrainedTokenizerBase:
    """Load pretrained tokenizer"""
    tokenizer = AutoTokenizer.from_pretrained(config.pretrained_model)
    return tokenizer


@step
def tokenization(
    config: TokenClassificationConfig,
    tokenizer: PreTrainedTokenizerBase,
    datasets: DatasetDict,
) -> DatasetDict:
    """Tokenizer dataset into tokens and then convert into encoded ids"""

    def tokenize_and_align_labels(examples):
        tokenized_inputs = tokenizer(
            examples[config.text_column],
            truncation=True,
            is_split_into_words=True,
        )

        labels = []
        for i, label in enumerate(examples[config.label_column]):
            word_ids = tokenized_inputs.word_ids(batch_index=i)
            previous_word_idx = None
            label_ids = []
            for word_idx in word_ids:
                # Special tokens have a word id that is None. We set the label to -100 so they are automatically
                # ignored in the loss function.
                if word_idx is None:
                    label_ids.append(-100)
                # We set the label for the first token of each word.
                elif word_idx != previous_word_idx:
                    label_ids.append(label[word_idx])
                # For the other tokens in a word, we set the label to either the current label or -100, depending on
                # the label_all_tokens flag.
                else:
                    label_ids.append(
                        label[word_idx] if config.label_all_tokens else -100
                    )
                previous_word_idx = word_idx

            labels.append(label_ids)

        tokenized_inputs["labels"] = labels
        return tokenized_inputs

    tokenized_datasets = datasets.map(tokenize_and_align_labels, batched=True)
    return tokenized_datasets


@step
def trainer(
    config: TokenClassificationConfig,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> TFPreTrainedModel:
    """Build and Train token classification model"""
    # Get label list
    label_list = (
        tokenized_datasets["train"].features[config.label_column].feature.names
    )

    # Load pre-trained model from huggingface hub
    model = TFAutoModelForTokenClassification.from_pretrained(
        config.pretrained_model, num_labels=len(label_list)
    )

    # Update label2id lookup
    model.config.label2id = {l: i for i, l in enumerate(label_list)}
    model.config.id2label = {i: l for i, l in enumerate(label_list)}

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
    model.compile(optimizer=optimizer)

    # Convert tokenized datasets into tf dataset
    train_set = tokenized_datasets["train"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=True,
        batch_size=config.batch_size,
        collate_fn=DataCollatorForTokenClassification(
            tokenizer, return_tensors="tf"
        ),
    )

    model.fit(train_set, epochs=config.epochs)
    return model


@step
def evaluator(
    config: TokenClassificationConfig,
    model: TFPreTrainedModel,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> float:
    """Evaluate trained model on validation set"""
    # Needs to recompile because we are reloading model for evaluation
    model.compile(optimizer=tf.keras.optimizers.Adam())

    # Convert into tf dataset format
    validation_set = tokenized_datasets["validation"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=False,
        batch_size=config.batch_size,
        collate_fn=DataCollatorForTokenClassification(
            tokenizer, return_tensors="tf"
        ),
    )

    # Calculate loss
    test_loss = model.evaluate(validation_set, verbose=1)
    return test_loss


@pipeline
def token_classifier_train_eval_pipeline(
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
