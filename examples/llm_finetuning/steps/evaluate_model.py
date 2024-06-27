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

from pathlib import Path
from typing import Optional

import evaluate
import torch
from datasets import load_from_disk
from utils.loaders import (
    load_base_model,
    load_pretrained_model,
)
from utils.tokenizer import load_tokenizer, tokenize_for_eval

from zenml import log_model_metadata, save_artifact, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def evaluate_model(
    base_model_id: str,
    system_prompt: str,
    datasets_dir: Path,
    ft_model_dir: Optional[Path],
    use_fast: bool = True,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
) -> None:
    """Evaluate the model with ROUGE metrics.

    Args:
        base_model_id: The base model id to use.
        system_prompt: The system prompt to use.
        datasets_dir: The path to the datasets directory.
        ft_model_dir: The path to the finetuned model directory. If None, the
            base model will be used.
        use_fast: Whether to use the fast tokenizer.
        load_in_4bit: Whether to load the model in 4bit mode.
        load_in_8bit: Whether to load the model in 8bit mode.
    """
    logger.info("Evaluating model...")

    logger.info("Loading dataset...")
    tokenizer = load_tokenizer(
        base_model_id,
        is_eval=True,
        use_fast=use_fast,
    )
    test_dataset = load_from_disk(datasets_dir / "test_raw")
    test_dataset = test_dataset[:50]
    ground_truths = test_dataset["meaning_representation"]
    tokenized_train_dataset = tokenize_for_eval(
        test_dataset, tokenizer, system_prompt
    )

    if ft_model_dir is None:
        logger.info("Generating using base model...")
        model = load_base_model(
            base_model_id,
            is_training=False,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
        )
    else:
        logger.info("Generating using finetuned model...")
        model = load_pretrained_model(
            ft_model_dir,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
        )

    model.eval()
    with torch.no_grad():
        predictions = model.generate(
            input_ids=tokenized_train_dataset["input_ids"],
            attention_mask=tokenized_train_dataset["attention_mask"],
            max_new_tokens=100,
            pad_token_id=2,
        )
    predictions = tokenizer.batch_decode(
        predictions[:, tokenized_train_dataset["input_ids"].shape[1] :],
        skip_special_tokens=True,
    )

    logger.info("Computing ROUGE metrics...")
    prefix = "base_model_" if ft_model_dir is None else "finetuned_model_"
    rouge = evaluate.load("rouge")
    rouge_metrics = rouge.compute(
        predictions=predictions, references=ground_truths
    )
    metadata = {prefix + k: float(v) for k, v in rouge_metrics.items()}

    log_model_metadata(metadata)
    logger.info("Computed metrics: " + str(metadata))

    save_artifact(rouge_metrics, prefix + "rouge_metrics")
