#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""A fine-tuned small-LLM student for Banking77 teacher decisions.

The student is the text backbone of a pinned Qwen3.5 checkpoint with a new
linear head over the final non-padding token. It learns only teacher hard
labels, like the lexical student, so the two students differ only in model
capacity and pretraining.

Torch and Transformers are imported inside functions so the rest of the
example, and its unit tests, run without GPU dependencies.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from examples.system_one_distillation.banking77_model import TeacherSupervision

QWEN_STUDENT_MODEL_ID = "Qwen/Qwen3.5-0.8B"
QWEN_STUDENT_MODEL_REVISION = "2fc06364715b967f1860aea9cf38778875588b17"
WEIGHTS_FILENAME = "student.safetensors"
METADATA_FILENAME = "student.json"


@dataclass(frozen=True)
class QwenStudentConfig:
    """Training recipe fixed before any held-out evaluation.

    Small rungs would otherwise receive only a handful of optimizer updates,
    so each rung trains for ``min_epochs`` or enough epochs to reach
    ``min_optimizer_steps``, whichever is larger.
    """

    model_id: str = QWEN_STUDENT_MODEL_ID
    model_revision: str = QWEN_STUDENT_MODEL_REVISION
    max_length: int = 64
    batch_size: int = 16
    eval_batch_size: int = 128
    backbone_learning_rate: float = 2e-5
    head_learning_rate: float = 1e-3
    weight_decay: float = 0.01
    warmup_fraction: float = 0.1
    min_epochs: int = 3
    min_optimizer_steps: int = 150
    seed: int = 13


@dataclass(frozen=True)
class QwenTrainingStats:
    """What one rung's training actually did."""

    epochs: int
    optimizer_steps: int
    truncated_count: int
    training_seconds: float


def planned_epochs(example_count: int, config: QwenStudentConfig) -> int:
    """Return the fixed epoch count for one rung size.

    Args:
        example_count: Number of teacher-labeled training examples.
        config: Fixed training recipe.

    Returns:
        Epochs that satisfy both the epoch and optimizer-step minimums.

    Raises:
        ValueError: If there are no training examples.
    """
    if example_count <= 0:
        raise ValueError("a rung needs at least one training example")
    steps_per_epoch = math.ceil(example_count / config.batch_size)
    return max(
        config.min_epochs,
        math.ceil(config.min_optimizer_steps / steps_per_epoch),
    )


@dataclass
class QwenStudent:
    """A trained backbone and head that predict taxonomy distributions."""

    taxonomy: tuple[str, ...]
    config: QwenStudentConfig
    training_example_ids: tuple[str, ...]
    backbone: Any
    head: Any
    tokenizer: Any
    device: str

    @property
    def parameter_count(self) -> int:
        """Total trainable parameters in the backbone and head.

        Returns:
            Parameter count.
        """
        return sum(
            parameter.numel()
            for module in (self.backbone, self.head)
            for parameter in module.parameters()
        )

    def release_gpu_memory(self) -> None:
        """Move weights to the CPU so the next rung has the whole GPU."""
        import torch

        self.backbone.to("cpu")
        self.head.to("cpu")
        self.device = "cpu"
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def predict_distributions(
        self, texts: Sequence[str]
    ) -> list[dict[str, float]]:
        """Predict a complete taxonomy distribution for each input.

        Inference runs in float32 on every device, so GPU-reported metrics
        and local predictions come from the same arithmetic as the saved
        weights. Mixed precision is used only for training speed.

        Args:
            texts: Text inputs in inference order.

        Returns:
            One probability per taxonomy label for every input.
        """
        import torch

        self.backbone.eval()
        self.head.eval()
        results: list[dict[str, float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), self.config.eval_batch_size):
                batch = _encode(
                    self.tokenizer,
                    texts[start : start + self.config.eval_batch_size],
                    self.config.max_length,
                    self.device,
                )
                logits = _logits(self.backbone, self.head, batch)
                probabilities = torch.softmax(logits.float(), dim=-1).cpu()
                results.extend(
                    dict(zip(self.taxonomy, row.tolist()))
                    for row in probabilities
                )
        return results


def train_qwen_student(
    examples: Sequence[TeacherSupervision],
    *,
    taxonomy: Sequence[str],
    config: QwenStudentConfig,
    device: str | None = None,
) -> tuple[QwenStudent, QwenTrainingStats]:
    """Fine-tune a fresh pretrained backbone on teacher hard labels.

    Args:
        examples: Ordered teacher-supervised inputs for one rung.
        taxonomy: Complete ordered set of allowed labels.
        config: Fixed training recipe.
        device: Torch device; defaults to CUDA, then MPS, then CPU.

    Returns:
        The trained student and a record of its training run.

    Raises:
        ValueError: If supervision is missing or outside the taxonomy.
    """
    import torch
    from transformers import get_linear_schedule_with_warmup

    labels = tuple(taxonomy)
    label_index = {label: index for index, label in enumerate(labels)}
    if not examples or any(
        example.teacher_label not in label_index for example in examples
    ):
        raise ValueError("every example needs a hard label in the taxonomy")

    device = device or _default_device()
    torch.manual_seed(config.seed)
    tokenizer, backbone = _load_pretrained(config)
    backbone.to(device)
    head = torch.nn.Linear(backbone.config.hidden_size, len(labels))
    torch.nn.init.normal_(head.weight, std=0.02)
    torch.nn.init.zeros_(head.bias)
    head.to(device)

    texts = [example.text for example in examples]
    targets = torch.tensor(
        [label_index[example.teacher_label] for example in examples]
    )
    truncated = sum(
        len(ids) > config.max_length
        for ids in tokenizer(texts, add_special_tokens=True)["input_ids"]
    )
    epochs = planned_epochs(len(examples), config)
    steps_per_epoch = math.ceil(len(examples) / config.batch_size)
    total_steps = epochs * steps_per_epoch
    optimizer = torch.optim.AdamW(
        [
            {
                "params": backbone.parameters(),
                "lr": config.backbone_learning_rate,
            },
            {"params": head.parameters(), "lr": config.head_learning_rate},
        ],
        weight_decay=config.weight_decay,
    )
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * config.warmup_fraction),
        num_training_steps=total_steps,
    )
    generator = torch.Generator().manual_seed(config.seed)

    started = time.perf_counter()
    backbone.train()
    head.train()
    for _ in range(epochs):
        order = torch.randperm(len(examples), generator=generator).tolist()
        for start in range(0, len(order), config.batch_size):
            indices = order[start : start + config.batch_size]
            batch = _encode(
                tokenizer,
                [texts[index] for index in indices],
                config.max_length,
                device,
            )
            with _autocast(device):
                logits = _logits(backbone, head, batch)
            loss = torch.nn.functional.cross_entropy(
                logits.float(), targets[indices].to(device)
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [*backbone.parameters(), *head.parameters()], 1.0
            )
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
    if device == "cuda":
        torch.cuda.synchronize()

    student = QwenStudent(
        taxonomy=labels,
        config=config,
        training_example_ids=tuple(example.example_id for example in examples),
        backbone=backbone,
        head=head,
        tokenizer=tokenizer,
        device=device,
    )
    stats = QwenTrainingStats(
        epochs=epochs,
        optimizer_steps=total_steps,
        truncated_count=truncated,
        training_seconds=time.perf_counter() - started,
    )
    return student, stats


def save_qwen_student(student: QwenStudent, directory: Path) -> Path:
    """Save full-precision weights and metadata.

    Weights stay in float32: rounding to bfloat16 changed individual
    probabilities by up to 0.17 in a smoke test, so a smaller file would no
    longer be the model the report scored.

    Args:
        student: Trained student.
        directory: Empty or missing output directory.

    Returns:
        The directory containing the weights and metadata.
    """
    from safetensors.torch import save_file

    directory.mkdir(parents=True, exist_ok=True)
    tensors = {
        **{
            f"backbone.{name}": value
            for name, value in student.backbone.state_dict().items()
        },
        **{
            f"head.{name}": value
            for name, value in student.head.state_dict().items()
        },
    }
    save_file(
        {
            name: value.detach().contiguous().cpu()
            for name, value in tensors.items()
        },
        str(directory / WEIGHTS_FILENAME),
    )
    (directory / METADATA_FILENAME).write_text(
        json.dumps(
            {
                "taxonomy": list(student.taxonomy),
                "config": asdict(student.config),
                "training_example_ids": list(student.training_example_ids),
            },
            indent=2,
        )
    )
    return directory


def load_qwen_student(
    directory: Path, device: str | None = None
) -> QwenStudent:
    """Rebuild a saved student from its pinned backbone configuration.

    Args:
        directory: Directory written by ``save_qwen_student``.
        device: Torch device; defaults to CUDA, then MPS, then CPU.

    Returns:
        The student ready for inference.
    """
    import torch
    from safetensors.torch import load_file
    from transformers import AutoConfig
    from transformers.models.qwen3_5 import Qwen3_5TextModel

    metadata = json.loads((directory / METADATA_FILENAME).read_text())
    config = QwenStudentConfig(**metadata["config"])
    taxonomy = tuple(metadata["taxonomy"])
    device = device or _default_device()
    model_config = AutoConfig.from_pretrained(
        config.model_id, revision=config.model_revision
    )
    backbone = Qwen3_5TextModel(model_config.text_config)
    head = torch.nn.Linear(backbone.config.hidden_size, len(taxonomy))
    tensors = load_file(str(directory / WEIGHTS_FILENAME))
    backbone.load_state_dict(
        {
            name.removeprefix("backbone."): value.float()
            for name, value in tensors.items()
            if name.startswith("backbone.")
        }
    )
    head.load_state_dict(
        {
            name.removeprefix("head."): value.float()
            for name, value in tensors.items()
            if name.startswith("head.")
        }
    )
    return QwenStudent(
        taxonomy=taxonomy,
        config=config,
        training_example_ids=tuple(metadata["training_example_ids"]),
        backbone=backbone.to(device),
        head=head.to(device),
        tokenizer=_load_tokenizer(config),
        device=device,
    )


def _load_pretrained(config: QwenStudentConfig) -> tuple[Any, Any]:
    """Load the pinned tokenizer and the checkpoint's text backbone only.

    The published checkpoint is multimodal; the vision tower is discarded
    because Banking77 inputs are text.

    Args:
        config: Training recipe naming the pinned checkpoint.

    Returns:
        Tokenizer and text backbone.
    """
    import torch
    from transformers import AutoModel

    full_model = AutoModel.from_pretrained(
        config.model_id, revision=config.model_revision, dtype=torch.float32
    )
    return _load_tokenizer(config), full_model.language_model


def _load_tokenizer(config: QwenStudentConfig) -> Any:
    """Load the pinned tokenizer with right padding.

    ``_logits`` finds each sequence's last real token by counting the
    attention mask, which is only correct when padding goes on the right.

    Args:
        config: Recipe naming the pinned checkpoint.

    Returns:
        The configured tokenizer.
    """
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.model_id, revision=config.model_revision
    )
    tokenizer.padding_side = "right"
    return tokenizer


def _encode(
    tokenizer: Any, texts: Sequence[str], max_length: int, device: str
) -> dict[str, Any]:
    """Tokenize one right-padded batch onto the target device.

    Args:
        tokenizer: Pinned tokenizer.
        texts: Batch inputs.
        max_length: Truncation length in tokens.
        device: Torch device.

    Returns:
        Input IDs and attention mask tensors.
    """
    encoded = tokenizer(
        list(texts),
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    return {name: value.to(device) for name, value in encoded.items()}


def _logits(backbone: Any, head: Any, batch: dict[str, Any]) -> Any:
    """Score the last non-padding token of each right-padded sequence.

    A causal backbone lets only the final token attend to the whole message,
    so it is the one position that summarizes every input token.

    Args:
        backbone: Text backbone returning ``last_hidden_state``.
        head: Linear classification head.
        batch: Input IDs and attention mask.

    Returns:
        Unnormalized label scores with shape ``[batch, labels]``.
    """
    import torch

    hidden = backbone(
        input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]
    ).last_hidden_state
    last = batch["attention_mask"].sum(dim=1) - 1
    pooled = hidden[torch.arange(hidden.shape[0], device=hidden.device), last]
    return head(pooled.to(head.weight.dtype))


def _autocast(device: str) -> Any:
    """Use bfloat16 autocast for CUDA training and full precision elsewhere.

    Args:
        device: Torch device.

    Returns:
        A context manager.
    """
    import torch

    return torch.autocast(
        device_type="cuda" if device == "cuda" else "cpu",
        dtype=torch.bfloat16,
        enabled=device == "cuda",
    )


def _default_device() -> str:
    """Pick the fastest available local torch device.

    Returns:
        ``cuda``, ``mps``, or ``cpu``.
    """
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
