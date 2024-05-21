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

import shutil
from pathlib import Path
from typing import Literal, Optional

import torch
from finetune.lora import setup
from huggingface_hub import upload_folder
from lit_gpt.args import EvalArgs, IOArgs, TrainArgs
from materializers.directory_materializer import DirectoryMaterializer
from pydantic import BaseModel
from scripts.convert_lit_checkpoint import convert_lit_checkpoint
from scripts.download import download_from_hub
from scripts.merge_lora import merge_lora
from scripts.prepare_alpaca import prepare
from typing_extensions import Annotated

from steps.params import LoraParameters
from steps.utils import (
    convert_to_lit_checkpoint_if_necessary,
    get_huggingface_access_token,
)
from zenml import get_step_context, log_model_metadata, step
from zenml.logger import get_logger
from zenml.materializers import BuiltInMaterializer

logger = get_logger(__file__)


class DataParameters(BaseModel):
    """Data preprocessing parameters."""

    seed: int = 42
    test_split_fraction: float = 0.03865
    mask_inputs: bool = False
    ignore_index: int = -1
    max_seq_length: Optional[int] = None


class TrainingParameters(BaseModel):
    """Training parameters."""

    save_interval: int = 1000
    log_interval: int = 1
    global_batch_size: int = 64
    micro_batch_size: int = 4
    lr_warmup_steps: int = 100
    epochs: Optional[int] = None
    epoch_size: Optional[int] = None
    max_tokens: Optional[int] = None
    max_seq_length: Optional[int] = None

    learning_rate: float = 1e-3
    weight_decay: float = 0.02
    beta1: float = 0.9
    beta2: float = 0.95
    max_norm: Optional[float] = None
    min_lr: float = 6e-5


class EvalParameters(BaseModel):
    """Mid-training evaluation parameters."""

    interval: int = 100
    max_new_tokens: int = 100
    max_iters: int = 100


class FinetuningParameters(BaseModel):
    """Parameters for the finetuning step."""

    base_model_repo: str
    from_safetensors: bool = False

    adapter_output_repo: Optional[str] = None
    merged_output_repo: Optional[str] = None
    convert_to_hf_checkpoint: bool = False

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

    data: DataParameters = DataParameters()
    training: TrainingParameters = TrainingParameters()
    eval: EvalParameters = EvalParameters()
    lora: LoraParameters = LoraParameters()


@step(output_materializers=[DirectoryMaterializer, BuiltInMaterializer])
def finetune(
    config: FinetuningParameters, dataset_directory: Optional[Path] = None
) -> Annotated[Optional[Path], "adapter"]:
    """Finetune model using LoRA.

    Args:
        config: Configuration for this step.
    """
    torch.set_float32_matmul_precision("high")

    access_token = get_huggingface_access_token()

    checkpoint_root_dir = Path("checkpoints")
    checkpoint_dir = checkpoint_root_dir / config.base_model_repo

    if checkpoint_dir.exists():
        logger.info(
            "Checkpoint directory already exists, skipping download..."
        )
    else:
        download_from_hub(
            repo_id=config.base_model_repo,
            from_safetensors=config.from_safetensors,
            checkpoint_dir=checkpoint_root_dir,
            access_token=access_token,
        )

    convert_to_lit_checkpoint_if_necessary(checkpoint_dir=checkpoint_dir)

    if dataset_directory:
        try:
            dataset_name = (
                get_step_context()
                .inputs["dataset_directory"]
                .run_metadata["dataset_name"]
                .value
            )
        except KeyError:
            dataset_name = "unknown_dataset"
    else:
        dataset_directory = Path("data/alpaca")
        dataset_name = dataset_directory.name
        prepare(
            destination_path=dataset_directory,
            checkpoint_dir=checkpoint_dir,
            test_split_fraction=config.data.test_split_fraction,
            seed=config.data.seed,
            mask_inputs=config.data.mask_inputs,
            ignore_index=config.data.ignore_index,
            max_seq_length=config.data.max_seq_length,
        )

    model_name = checkpoint_dir.name

    log_model_metadata(
        metadata={"model_name": model_name, "dataset_name": dataset_name}
    )
    adapter_output_dir = Path("output/lora") / dataset_name / model_name

    io_args = IOArgs(
        train_data_dir=dataset_directory,
        val_data_dir=dataset_directory,
        checkpoint_dir=checkpoint_dir,
        out_dir=adapter_output_dir,
    )
    train_args = TrainArgs(**config.training.dict())
    eval_args = EvalArgs(**config.eval.dict())
    setup(
        devices=1,
        io=io_args,
        train=train_args,
        eval=eval_args,
        precision=config.precision,
        quantize=config.quantize,
        **config.lora.dict(),
    )

    if config.merged_output_repo:
        lora_path = adapter_output_dir / "lit_model_lora_finetuned.pth"

        merge_output_dir = (
            Path("output/lora_merged") / dataset_name / model_name
        )
        merge_lora(
            lora_path=lora_path,
            checkpoint_dir=checkpoint_dir,
            out_dir=merge_output_dir,
            precision=config.precision,
            **config.lora.dict(),
        )

        for path in Path(checkpoint_dir).glob("*.json"):
            destination = Path(merge_output_dir) / path.name
            shutil.copy(src=path, dst=destination)

        if config.convert_to_hf_checkpoint:
            upload_dir = (
                Path("output/lora_merged_hf") / dataset_name / model_name
            )
            upload_dir.mkdir(parents=True, exist_ok=True)
            convert_lit_checkpoint(
                checkpoint_path=config.merged_output_repo / "lit_model.pth",
                config_path=config.merged_output_repo / "lit_config.json",
                output_path=upload_dir / "pytorch_model",
            )
        else:
            upload_dir = merge_output_dir

        commit = upload_folder(
            repo_id=config.merged_output_repo,
            folder_path=upload_dir,
            token=access_token,
        )
        log_model_metadata(
            metadata={
                "merged_model_huggingface_commit_hash": commit.oid,
                "merged_model_huggingface_commit_url": commit.commit_url,
            }
        )

    if config.adapter_output_repo:
        commit = upload_folder(
            repo_id=config.adapter_output_repo,
            folder_path=adapter_output_dir,
            token=access_token,
        )
        log_model_metadata(
            metadata={
                "adapter_huggingface_commit_hash": commit.oid,
                "adapter_huggingface_commit_url": commit.commit_url,
            }
        )
        return None
    else:
        # If the adapter should not be uploaded to the HF Hub, we store it
        # in the artifact store
        return adapter_output_dir
