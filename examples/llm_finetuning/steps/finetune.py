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

import transformers
from accelerate import Accelerator
from datasets import load_from_disk
from materializers.directory_materializer import DirectoryMaterializer
from typing_extensions import Annotated
from utils.callbacks import ZenMLCallback
from utils.loaders import load_base_model
from utils.tokenizer import load_tokenizer

from zenml import ArtifactConfig, step
from zenml.logger import get_logger
from zenml.materializers import BuiltInMaterializer
from zenml.utils.cuda_utils import cleanup_gpu_memory

logger = get_logger(__name__)


@step(output_materializers=[DirectoryMaterializer, BuiltInMaterializer])
def finetune(
    base_model_id: str,
    dataset_dir: Path,
    max_steps: int = 1000,
    logging_steps: int = 50,
    eval_steps: int = 50,
    save_steps: int = 50,
    optimizer: str = "paged_adamw_8bit",
    lr: float = 2.5e-5,
    per_device_train_batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
    warmup_steps: int = 5,
    bf16: bool = True,
    use_accelerate: bool = False,
    use_fast: bool = True,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
) -> Annotated[
    Path, ArtifactConfig(name="ft_model_dir", is_model_artifact=True)
]:
    """Finetune the model using PEFT.

    Base model will be derived from configure step and finetuned model will
    be saved to the output directory.

    Finetuning parameters can be found here: https://github.com/huggingface/peft#fine-tuning

    Args:
        base_model_id: The base model id to use.
        dataset_dir: The path to the dataset directory.
        max_steps: The maximum number of steps to train for.
        logging_steps: The number of steps to log at.
        eval_steps: The number of steps to evaluate at.
        save_steps: The number of steps to save at.
        optimizer: The optimizer to use.
        lr: The learning rate to use.
        per_device_train_batch_size: The batch size to use for training.
        gradient_accumulation_steps: The number of gradient accumulation steps.
        warmup_steps: The number of warmup steps.
        bf16: Whether to use bf16.
        use_accelerate: Whether to use accelerate.
        use_fast: Whether to use the fast tokenizer.
        load_in_4bit: Whether to load the model in 4bit mode.
        load_in_8bit: Whether to load the model in 8bit mode.

    Returns:
        The path to the finetuned model directory.
    """
    cleanup_gpu_memory(force=True)

    ft_model_dir = Path("model_dir")
    dataset_dir = Path(dataset_dir)

    if use_accelerate:
        accelerator = Accelerator()
        should_print = accelerator.is_main_process
    else:
        accelerator = None
        should_print = True

    project = "zenml-finetune"
    run_name = base_model_id + "-" + project
    output_dir = "./" + run_name

    if should_print:
        logger.info("Loading datasets...")
    tokenizer = load_tokenizer(base_model_id, use_fast=use_fast)
    tokenized_train_dataset = load_from_disk(dataset_dir / "train")
    tokenized_val_dataset = load_from_disk(dataset_dir / "val")

    if should_print:
        logger.info("Loading base model...")

    model = load_base_model(
        base_model_id,
        use_accelerate=use_accelerate,
        should_print=should_print,
        load_in_4bit=load_in_4bit,
        load_in_8bit=load_in_8bit,
    )

    trainer = transformers.Trainer(
        model=model,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_val_dataset,
        args=transformers.TrainingArguments(
            output_dir=output_dir,
            warmup_steps=warmup_steps,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_checkpointing=(not use_accelerate),
            gradient_accumulation_steps=gradient_accumulation_steps,
            max_steps=max_steps,
            learning_rate=lr,
            logging_steps=(
                min(logging_steps, max_steps)
                if max_steps >= 0
                else logging_steps
            ),
            bf16=bf16,
            optim=optimizer,
            logging_dir="./logs",
            save_strategy="steps",
            save_steps=min(save_steps, max_steps)
            if max_steps >= 0
            else save_steps,
            evaluation_strategy="steps",
            eval_steps=eval_steps,
            do_eval=True,
            label_names=["input_ids"],
        ),
        data_collator=transformers.DataCollatorForLanguageModeling(
            tokenizer, mlm=False
        ),
        callbacks=[ZenMLCallback(accelerator=accelerator)],
    )
    if not use_accelerate:
        model.config.use_cache = (
            False  # silence the warnings. Please re-enable for inference!
        )

    if should_print:
        logger.info("Training model...")
    trainer.train()

    if should_print:
        logger.info("Saving model...")

    ft_model_dir = Path(ft_model_dir)
    if not use_accelerate or accelerator.is_main_process:
        ft_model_dir.mkdir(parents=True, exist_ok=True)
    if not use_accelerate:
        model.config.use_cache = True
        trainer.save_model(ft_model_dir)
    else:
        unwrapped_model = accelerator.unwrap_model(model)
        unwrapped_model.save_pretrained(
            ft_model_dir,
            is_main_process=accelerator.is_main_process,
            save_function=accelerator.save,
        )

    return ft_model_dir
