# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
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
from typing import Any, Tuple, Union

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM

from utils.logging import print_trainable_parameters


def load_base_model(
    base_model_id: str,
    is_training: bool = True,
    use_accelerate: bool = False,
    should_print: bool = True,
    load_in_8bit: bool = False,
    load_in_4bit: bool = False,
) -> Union[Any, Tuple[Any, Dataset, Dataset]]:
    """Load the base model.

    Args:
        base_model_id: The base model id to use.
        is_training: Whether the model should be prepared for training or not.
            If True, the Lora parameters will be enabled and PEFT will be
            applied.
        use_accelerate: Whether to use the Accelerate library for training.
        should_print: Whether to print the trainable parameters.
        load_in_8bit: Whether to load the model in 8-bit mode.
        load_in_4bit: Whether to load the model in 4-bit mode.

    Returns:
        The base model.
    """
    from accelerate import Accelerator
    from transformers import BitsAndBytesConfig

    if use_accelerate:
        accelerator = Accelerator()
        device_map = {"": accelerator.process_index}
    else:
        device_map = {"": torch.cuda.current_device()}

    bnb_config = BitsAndBytesConfig(
        load_in_8bit=load_in_8bit,
        load_in_4bit=load_in_4bit,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id, quantization_config=bnb_config, device_map=device_map
    )

    if is_training:
        model.gradient_checkpointing_enable()
        model = prepare_model_for_kbit_training(model)

        config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
                "lm_head",
            ],
            bias="none",
            lora_dropout=0.05,  # Conventional
            task_type="CAUSAL_LM",
        )

        model = get_peft_model(model, config)
        if should_print:
            print_trainable_parameters(model)
        if use_accelerate:
            model = accelerator.prepare_model(model)

    return model


def load_pretrained_model(
    ft_model_dir: Path,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
) -> AutoModelForCausalLM:
    """Load the finetuned model saved in the output directory.

    Args:
        ft_model_dir: The path to the finetuned model directory.
        load_in_4bit: Whether to load the model in 4-bit mode.
        load_in_8bit: Whether to load the model in 8-bit mode.

    Returns:
        The finetuned model.
    """
    from transformers import BitsAndBytesConfig

    bnb_config = BitsAndBytesConfig(
        load_in_8bit=load_in_8bit,
        load_in_4bit=load_in_4bit,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        ft_model_dir, quantization_config=bnb_config, device_map="auto"
    )
    return model
