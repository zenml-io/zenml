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


from steps import (
    evaluate_model,
    finetune,
    log_metadata_from_step_artifact,
    prepare_data,
    promote,
)

from zenml import pipeline


@pipeline
def llm_peft_full_finetune(
    system_prompt: str,
    base_model_id: str,
    use_fast: bool = True,
    load_in_8bit: bool = False,
    load_in_4bit: bool = False,
):
    """Pipeline for finetuning an LLM with PEFT.

    It will run the following steps:

    - prepare_data: prepare the datasets and tokenize them
    - finetune: finetune the model
    - evaluate_model: evaluate the base and finetuned model
    - promote: promote the model to the target stage, if evaluation was successful
    """
    if not load_in_8bit and not load_in_4bit:
        raise ValueError(
            "At least one of `load_in_8bit` and `load_in_4bit` must be True."
        )
    if load_in_4bit and load_in_8bit:
        raise ValueError(
            "Only one of `load_in_8bit` and `load_in_4bit` can be True."
        )

    datasets_dir = prepare_data(
        base_model_id=base_model_id,
        system_prompt=system_prompt,
        use_fast=use_fast,
    )

    evaluate_model(
        base_model_id,
        system_prompt,
        datasets_dir,
        None,
        use_fast=use_fast,
        load_in_8bit=load_in_8bit,
        load_in_4bit=load_in_4bit,
        id="evaluate_base",
    )
    log_metadata_from_step_artifact(
        "evaluate_base",
        "base_model_rouge_metrics",
        after=["evaluate_base"],
        id="log_metadata_evaluation_base",
    )

    ft_model_dir = finetune(
        base_model_id,
        datasets_dir,
        use_fast=use_fast,
        load_in_8bit=load_in_8bit,
        load_in_4bit=load_in_4bit,
    )

    evaluate_model(
        base_model_id,
        system_prompt,
        datasets_dir,
        ft_model_dir,
        use_fast=use_fast,
        load_in_8bit=load_in_8bit,
        load_in_4bit=load_in_4bit,
        id="evaluate_finetuned",
    )
    log_metadata_from_step_artifact(
        "evaluate_finetuned",
        "finetuned_model_rouge_metrics",
        after=["evaluate_finetuned"],
        id="log_metadata_evaluation_finetuned",
    )

    promote(
        after=[
            "log_metadata_evaluation_finetuned",
            "log_metadata_evaluation_base",
        ]
    )
