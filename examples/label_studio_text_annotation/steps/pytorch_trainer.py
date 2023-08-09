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
import os
import tempfile
from typing import Dict, List
from urllib.parse import urlparse

import evaluate
import numpy as np
import torch
import torch.nn as nn
from steps.configuration import HuggingfaceParameters
from steps.get_or_create_dataset import LABELS
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from zenml.integrations.label_studio.label_studio_utils import (
    get_file_extension,
    is_azure_url,
    is_gcs_url,
    is_s3_url,
)
from zenml.io import fileio
from zenml.post_execution import get_pipeline
from zenml.steps import step
from zenml.steps.step_context import StepContext
from zenml.utils import io_utils

LABEL_MAPPING = {label: idx for idx, label in enumerate(LABELS)}

PIPELINE_NAME = "training_pipeline"
PIPELINE_STEP_NAME = "model_trainer"


class CustomDataset:
    """Creates a dataset to be used in the PyTorch model training."""

    def __init__(self, text_urls, labels, artifact_store_path: str) -> None:
        assert len(text_urls) == len(labels)

        # Download all images from the artifact store as np.ndarray
        self.texts = []
        temp_dir = tempfile.TemporaryDirectory()
        for i, text_url in enumerate(text_urls):
            parts = text_url.split("/")
            if is_s3_url(text_url):
                file_url = f"{artifact_store_path}{urlparse(text_url).path}"
            elif is_azure_url(text_url):
                file_url = "az://" + "/".join(parts[3:])
            elif is_gcs_url(text_url):
                url_scheme = "gs"
                url_path = urlparse(text_url).path
                file_url = f"{url_scheme}://{url_path}"
            file_extension = get_file_extension(urlparse(text_url).path)
            path = os.path.join(temp_dir.name, f"{i}{file_extension}")
            io_utils.copy(file_url, path)
            with fileio.open(path, "r", encoding="utf-8") as file:
                self.texts.append(file.readlines()[0])
        fileio.rmtree(temp_dir.name)

        # Define class-label mapping and map labels
        self.class_label_mapping = LABEL_MAPPING
        self.labels = [self.class_label_mapping[label] for label in labels]

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        return (text, label)

    def __len__(self):
        return len(self.texts)


def _find_last_successful_run(context: StepContext) -> int:
    """Get the index of the last successful run of this pipeline and step."""
    pipeline = get_pipeline(PIPELINE_NAME)
    if pipeline is not None:
        for idx, run in reversed(list(enumerate(pipeline.runs))):
            try:
                run.get_step(PIPELINE_STEP_NAME).output.read()
                return idx
            except (KeyError, ValueError):  # step didn't run or had no output
                pass
    return None


def _load_last_model(context: StepContext) -> nn.Module:
    """Return the most recently trained model from this pipeline, or None."""
    idx = _find_last_successful_run(context=context)
    if idx is None:
        return None
    last_run = get_pipeline(PIPELINE_NAME).runs[idx]
    return last_run.get_step(PIPELINE_STEP_NAME).output.read()


def _is_new_data_available(
    text_urls: List[str],
    context: StepContext,
) -> bool:
    """Find whether new data is available since the last run."""
    # If there are no samples, nothing can be new.
    num_samples = len(text_urls)
    if num_samples == 0:
        return False

    # Otherwise, if there was no previous run, the data is for sure new.
    idx = _find_last_successful_run(context=context)
    if idx is None:
        return True

    # Else, we check whether we had the same number of samples before.
    last_run = get_pipeline(PIPELINE_NAME).runs[idx]
    last_inputs = last_run.get_step(PIPELINE_STEP_NAME).inputs
    last_text_urls = last_inputs["image_urls"].read()
    return len(last_text_urls) != len(text_urls)


@step(enable_cache=False)
def pytorch_model_trainer(
    text_urls: List[str],
    labels: List[Dict[str, str]],
    params: HuggingfaceParameters,
    context: StepContext,
) -> (
    nn.Module
):  # transformers.pipelines.text_classification.TextClassificationPipeline:
    """ZenML step which finetunes or loads a pretrained mobilenetv3 model."""
    # Try to load a model from a previous run, otherwise use a pretrained net
    # model = _load_last_model(context=context)
    # if model is None:
    model = AutoModelForSequenceClassification.from_pretrained(
        params.pretrained_model, num_labels=len(LABELS)
    )
    tokenizer = AutoTokenizer.from_pretrained(params.pretrained_model)

    # If there is no new data, just return the model
    if not _is_new_data_available(text_urls, context):
        return model

    artifact_store_path = context.stack.artifact_store.path

    # Otherwise finetune the model on the current data
    # Write images and labels to torch dataset
    dataset = CustomDataset(
        text_urls=text_urls,
        labels=labels,
        artifact_store_path=artifact_store_path,
    )

    # Split dataset into train and val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset=dataset,
        lengths=[train_size, val_size],
        generator=torch.Generator(),
    )
    dataset_dict = {
        "train": train_dataset,
        "val": val_dataset,
    }

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    f1_score = evaluate.load("f1")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return f1_score.compute(predictions=predictions, references=labels)

    training_args = TrainingArguments(
        output_dir="my_awesome_model",
        learning_rate=params.init_lr,
        per_device_train_batch_size=params.batch_size,
        per_device_eval_batch_size=params.batch_size,
        num_train_epochs=params.epochs,
        weight_decay=params.weight_decay_rate,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset_dict["train"],
        eval_dataset=dataset_dict["val"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.evaluate()

    return trainer.model
