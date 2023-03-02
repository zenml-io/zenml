#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Optional

import click
from pipelines import (
    seq_classifier_train_eval_pipeline,
    token_classifier_train_eval_pipeline,
)
from steps import (
    data_importer,
    load_tokenizer,
    sequence_classifier_tokenization,
    sequence_evaluator,
    sequence_trainer,
    token_classification_tokenization,
    token_evaluator,
    token_trainer,
)
from steps.configuration import HuggingfaceParameters


@click.command()
@click.option(
    "--nlp_task",
    type=click.Choice(["token-classification", "sequence-classification"]),
    default="sequence-classification",
    help="Name NLP task i.e. token-classification, sequence-classification",
)
@click.option(
    "--pretrained_model",
    default="distilbert-base-uncased",
    help="Pretrained model name from huggingface hub",
)
@click.option(
    "--batch_size",
    default=8,
    help="Batch Size for training",
)
@click.option(
    "--full_set",
    is_flag=True,
    help="By default only a very small subset of the datasets is used in order "
    "to have a quick end-to-end run. By running with the full datasets "
    "the runtime increases significantly.",
)
@click.option(
    "--epochs",
    default=1,
    help="Number of epochs for training",
)
@click.option(
    "--max_seq_length",
    default=128,
    help="Max sequence length for training",
)
@click.option(
    "--init_lr",
    default=2e-5,
    help="Initial learning rate for training",
)
@click.option(
    "--weight_decay_rate",
    default=0.01,
    help="Weight decay rate for training",
)
@click.option(
    "--text_column",
    help="Column name for text in the dataset. i.e. For sequence "
    "classification, this will be text and for token classification, "
    "this will be tokens",
)
@click.option(
    "--label_column",
    help="Column name for label in the dataset. i.e For sequence"
    " classification, this will be label and for token classification, "
    "this will be ner_tags",
)
@click.option(
    "--dataset_name",
    help="Name of the dataset to be used. i.e For sequence classification, "
    "this will be imdb and for token classification, this will be "
    "conll2003",
)
def main(
    nlp_task: str,
    pretrained_model: str,
    batch_size: int,
    epochs: int,
    full_set: bool,
    max_seq_length: int,
    init_lr: float,
    weight_decay_rate: float,
    text_column: Optional[str] = None,
    label_column: Optional[str] = None,
    dataset_name: Optional[str] = None,
):
    if nlp_task == "token-classification":
        if not text_column:
            text_column = "tokens"
        if not label_column:
            label_column = "ner_tags"
        if not dataset_name:
            dataset_name = "conll2003"

        token_classification_config = HuggingfaceParameters(
            label_all_tokens=True,
            pretrained_model=pretrained_model,
            epochs=epochs,
            batch_size=batch_size,
            max_seq_length=max_seq_length,
            init_lr=init_lr,
            weight_decay_rate=weight_decay_rate,
            dummy_run=not full_set,
            dataset_name=dataset_name,
            text_column=text_column,
            label_column=label_column,
        )
        pipeline = token_classifier_train_eval_pipeline(
            importer=data_importer(token_classification_config),
            load_tokenizer=load_tokenizer(token_classification_config),
            tokenization=token_classification_tokenization(
                token_classification_config
            ),
            trainer=token_trainer(token_classification_config),
            evaluator=token_evaluator(token_classification_config),
        )
        pipeline.run()

    elif nlp_task == "sequence-classification":
        if not text_column:
            text_column = "text"
        if not label_column:
            label_column = "label"
        if not dataset_name:
            dataset_name = "imdb"

        sequence_classification_config = HuggingfaceParameters(
            pretrained_model=pretrained_model,
            epochs=epochs,
            batch_size=batch_size,
            dummy_run=not full_set,
            max_seq_length=max_seq_length,
            init_lr=init_lr,
            weight_decay_rate=weight_decay_rate,
            dataset_name=dataset_name,
            text_column=text_column,
            label_column=label_column,
        )
        pipeline = seq_classifier_train_eval_pipeline(
            importer=data_importer(sequence_classification_config),
            load_tokenizer=load_tokenizer(sequence_classification_config),
            tokenization=sequence_classifier_tokenization(
                sequence_classification_config
            ),
            trainer=sequence_trainer(sequence_classification_config),
            evaluator=sequence_evaluator(sequence_classification_config),
        )
        pipeline.run()


if __name__ == "__main__":
    main()
