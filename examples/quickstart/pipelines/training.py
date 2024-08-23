# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import materializers
from steps import (
    evaluate_model,
    load_data,
    split_dataset,
    test_model,
    tokenize_data,
    train_model,
)
from steps.model_trainer import T5_Model

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)

assert materializers  # Ensure materializers are loaded


@pipeline
def english_translation_pipeline(
    model_type: T5_Model,
    per_device_train_batch_size: int,
    gradient_accumulation_steps: int,
    dataloader_num_workers: int,
    num_train_epochs: int = 5,
):
    """Define a pipeline that connects the steps."""
    full_dataset = load_data()
    tokenized_dataset, tokenizer = tokenize_data(
        dataset=full_dataset, model_type=model_type
    )
    tokenized_train_dataset, tokenized_eval_dataset, tokenized_test_dataset = (
        split_dataset(tokenized_dataset)
    )
    model = train_model(
        tokenized_dataset=tokenized_train_dataset,
        model_type=model_type,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        dataloader_num_workers=dataloader_num_workers,
    )
    evaluate_model(model=model, tokenized_dataset=tokenized_eval_dataset)
    test_model(
        model=model,
        tokenized_test_dataset=tokenized_test_dataset,
        tokenizer=tokenizer,
    )
