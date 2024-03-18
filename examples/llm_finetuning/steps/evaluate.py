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

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import torch
from evaluate.lm_eval_harness import run_eval_harness
from huggingface_hub import snapshot_download
from pydantic import BaseModel
from scripts.download import download_from_hub
from scripts.merge_lora import merge_lora
from typing_extensions import Annotated

from steps.params import LoraParameters
from steps.utils import (
    convert_to_lit_checkpoint_if_necessary,
    get_huggingface_access_token,
)
from zenml import step
from zenml.logger import get_logger

logger = get_logger(__file__)


class EvaluationParameters(BaseModel):
    """Parameters for the evaluation step.

    If `adapter_repo` is set, it will be merged with the model. Otherwise
    the model itself will be evaluated.
    """

    model_repo: str
    from_safetensors: bool = False
    adapter_repo: Optional[str] = None

    precision: Optional[str] = None
    quantize: Optional[
        Literal[
            "bnb.nf4",
            "bnb.nf4-dq",
            "bnb.fp4",
            "bnb.fp4-dq",
            "bnb.int8-training",
        ]
    ] = None

    lora: LoraParameters = LoraParameters()

    eval_tasks: List[str] = [
        "arc_challenge",
        "piqa",
        "hellaswag",
        "hendrycksTest-*",
    ]
    num_fewshot: int = 0
    limit: Optional[int] = None
    bootstrap_iters: int = 100000
    no_cache: bool = True


@step
def evaluate(
    config: EvaluationParameters,
) -> Annotated[Dict[str, Any], "evaluation_results"]:
    """Evaluate model.

    Args:
        config: Configuration for this step.
    """
    torch.set_float32_matmul_precision("high")

    access_token = get_huggingface_access_token()

    checkpoint_root_dir = Path("checkpoints")
    checkpoint_dir = checkpoint_root_dir / config.model_repo

    if checkpoint_dir.exists():
        logger.info(
            "Checkpoint directory already exists, skipping download..."
        )
    else:
        download_from_hub(
            repo_id=config.model_repo,
            from_safetensors=config.from_safetensors,
            checkpoint_dir=checkpoint_root_dir,
            access_token=access_token,
        )

    convert_to_lit_checkpoint_if_necessary(checkpoint_dir=checkpoint_dir)

    if config.adapter_repo:
        adapter_dir = Path("adapters") / config.adapter_repo
        merged_dir = Path("output/merged")

        snapshot_download(
            config.adapter_repo,
            local_dir=adapter_dir,
            local_dir_use_symlinks=False,
            resume_download=True,
            token=access_token,
        )

        lora_path = adapter_dir / "lit_model_lora_finetuned.pth"
        merge_lora(
            lora_path=lora_path,
            checkpoint_dir=checkpoint_dir,
            out_dir=merged_dir,
            precision=config.precision,
            **config.lora.dict(),
        )

        for path in Path(checkpoint_dir).glob("*.json"):
            destination = Path(merged_dir) / path.name
            shutil.copy(src=path, dst=destination)

        checkpoint_dir = merged_dir

    output_path = Path("output.json")
    run_eval_harness(
        checkpoint_dir=checkpoint_dir,
        save_filepath=output_path,
        **config.dict(exclude={"model_repo", "adapter_repo", "lora"}),
    )

    with open(output_path, "r") as f:
        return json.load(f)
