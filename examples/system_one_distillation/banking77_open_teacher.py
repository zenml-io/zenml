#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.

"""Open-weight Jev-style teacher for the Banking77 experiment."""

import math
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from examples.system_one_distillation.banking77_data import (
    Banking77TeacherInput,
)
from examples.system_one_distillation.contracts import ContractModel
from pydantic import Field

from zenml.logger import get_logger

logger = get_logger(__name__)

OPEN_TEACHER_MODEL_ID = "ZefanCai/Open-Jev-27B-v1.1"
OPEN_TEACHER_MODEL_REVISION = "28cf73067d5b337860bbef3c85b8b82ba8730956"
OPEN_TEACHER_CODE_REVISION = "3308a15ccd7eea1df7a37d6ddc39b023b801ba16"


class Banking77OpenTeacherLabel(ContractModel):
    """One complete distribution returned by the pinned open teacher."""

    example_id: str = Field(min_length=1)
    chosen_label: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]
    input_tokens: int = Field(ge=0)
    latency_seconds: float = Field(ge=0.0)
    model_id: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    code_revision: str = Field(min_length=1)


class OpenTeacherRun(ContractModel):
    """Open-teacher labels and aggregate runtime evidence."""

    labels: tuple[Banking77OpenTeacherLabel, ...]
    elapsed_seconds: float = Field(ge=0.0)
    decisions_per_second: float = Field(ge=0.0)
    prefix_cache: bool
    worker_elapsed_seconds: tuple[float, ...] = ()


def normalize_choice_distribution(
    probabilities: Mapping[str, Any], *, taxonomy: Sequence[str]
) -> dict[str, float]:
    """Validate and normalize one complete open-teacher distribution.

    Args:
        probabilities: Raw probability mapping returned by Open-Jev.
        taxonomy: Exact ordered choice keys expected by the experiment.

    Returns:
        A complete normalized distribution in taxonomy order.

    Raises:
        ValueError: If keys or probability values are invalid.
    """
    labels = tuple(taxonomy)
    if not labels or len(set(labels)) != len(labels):
        raise ValueError("taxonomy must contain unique labels")
    if set(probabilities) != set(labels):
        raise ValueError(
            "open-teacher probability keys do not match the taxonomy"
        )
    values: list[float] = []
    for label in labels:
        value = probabilities[label]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("open-teacher probabilities must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0.0:
            raise ValueError(
                "open-teacher probabilities must be finite and nonnegative"
            )
        values.append(numeric)
    total = sum(values)
    if total <= 0.0:
        raise ValueError(
            "open-teacher probabilities must contain positive mass"
        )
    return {label: value / total for label, value in zip(labels, values)}


def label_with_open_teacher(
    inputs: Sequence[Banking77TeacherInput],
    *,
    batch_size: int = 32,
    device: str = "cuda:0",
    prefix_cache: bool = False,
    model_id: str = OPEN_TEACHER_MODEL_ID,
    model_revision: str = OPEN_TEACHER_MODEL_REVISION,
) -> OpenTeacherRun:
    """Label Banking77 directly with the pinned 27B open teacher.

    The model scores each caller-supplied candidate independently before one
    normalization over all 77 intents. Its published training manifest does
    not contain Banking77, so these labels remain a zero-shot teacher signal.

    Args:
        inputs: Label-free Banking77 inputs.
        batch_size: Maximum candidate sequences scored per model batch.
        device: Torch device for the 27B model.
        prefix_cache: Reuse the shared request prefix. Disabled for the primary
            result because the model card identifies uncached inference as its
            conservative validated path.
        model_id: Hugging Face repository containing the adapter package.
        model_revision: Exact model repository commit.

    Returns:
        Complete teacher distributions and aggregate throughput.

    Raises:
        ValueError: If configuration or model output is invalid.
        RuntimeError: If the optional Open-Jev runtime is unavailable.
    """
    if not inputs or batch_size < 1:
        raise ValueError("inputs and a positive batch_size are required")
    if len({item.example_id for item in inputs}) != len(inputs):
        raise ValueError("Banking77 teacher input IDs must be unique")
    taxonomy = tuple(inputs[0].question.criteria)
    if len(taxonomy) != 77 or any(
        tuple(item.question.criteria) != taxonomy for item in inputs
    ):
        raise ValueError("all inputs must share the exact 77-intent taxonomy")
    try:
        from huggingface_hub import snapshot_download
        from jev.serving import load_predictor
    except ImportError as exc:
        raise RuntimeError(
            "Install the pinned Open-Jev runtime and huggingface-hub."
        ) from exc

    logger.info(
        "Downloading the pinned open teacher %s at revision %s.",
        model_id,
        model_revision,
    )
    snapshot = Path(
        snapshot_download(repo_id=model_id, revision=model_revision)
    )
    logger.info("Loading the open teacher on %s.", device)
    predictor = load_predictor(
        checkpoint=snapshot / "package" / "checkpoint",
        device=device,
        max_length=4096,
        batch_size=batch_size,
        prefix_cache=prefix_cache,
    )
    started = time.perf_counter()
    labels: list[Banking77OpenTeacherLabel] = []
    for index, item in enumerate(inputs, start=1):
        response = predictor.predict(
            {
                "state": item.text,
                "questions": {"intent": item.question.model_dump(mode="json")},
            }
        )
        answer = response["answers"]["intent"]
        probabilities = normalize_choice_distribution(
            answer["probabilities"], taxonomy=taxonomy
        )
        choice = answer["choice"]
        if choice not in probabilities:
            raise ValueError(
                f"open teacher chose an unknown label for {item.example_id!r}"
            )
        labels.append(
            Banking77OpenTeacherLabel(
                example_id=item.example_id,
                chosen_label=choice,
                confidence=answer["confidence"],
                probabilities=probabilities,
                input_tokens=response["usage"]["input_tokens"],
                latency_seconds=response["metadata"]["inference_seconds"],
                model_id=model_id,
                model_revision=model_revision,
                code_revision=OPEN_TEACHER_CODE_REVISION,
            )
        )
        if index % 100 == 0 or index == len(inputs):
            running_elapsed = max(0.0, time.perf_counter() - started)
            logger.info(
                "Open teacher labeled %d/%d inputs at %.3f decisions/s.",
                index,
                len(inputs),
                index / running_elapsed if running_elapsed else 0.0,
            )
    elapsed = max(0.0, time.perf_counter() - started)
    return OpenTeacherRun(
        labels=tuple(labels),
        elapsed_seconds=elapsed,
        decisions_per_second=(len(inputs) / elapsed if elapsed else 0.0),
        prefix_cache=prefix_cache,
        worker_elapsed_seconds=(elapsed,),
    )
