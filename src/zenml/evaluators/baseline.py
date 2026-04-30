#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Resolve a baseline EvaluationResult to compare against."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.client import Client
from zenml.evaluators.result import EvaluationMode, EvaluationResult
from zenml.logger import get_logger

logger = get_logger(__name__)


BaselineStrategy = Literal["explicit", "model_registry", "none"]


class BaselineSpec(BaseModel):
    """How to resolve the baseline for a given evaluator run."""

    strategy: BaselineStrategy = "model_registry"
    artifact_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    model_version_id: Optional[UUID] = None  # override: pull from this version


def resolve_baseline(
    spec: BaselineSpec,
    suite_name: str,
    mode: EvaluationMode,
) -> Optional[EvaluationResult]:
    """Resolve the baseline EvaluationResult, or None if there isn't one.

    Strategies:
      - "explicit": fetch the EvaluationResult by artifact_id or run_id.
        Raises if neither is provided.
      - "model_registry": pull the latest EvaluationResult linked to the
        production model version, filtered by suite_name and mode. Returns
        None gracefully if no registry is configured or no production
        version exists.
      - "none": always returns None.

    Args:
        spec: Baseline configuration.
        suite_name: Logical join key for matching baseline to current.
        mode: Eval mode of the current run; baseline must match.

    Returns:
        The baseline EvaluationResult, or None.

    Raises:
        ValueError: If the strategy is unknown, or if "explicit" is requested
            without an artifact_id or run_id.
    """
    if spec.strategy == "none":
        return None

    if spec.strategy == "explicit":
        return _resolve_explicit(spec)

    if spec.strategy == "model_registry":
        return _resolve_from_model_registry(spec, suite_name, mode)

    raise ValueError(f"Unknown baseline strategy: {spec.strategy}")


def _resolve_explicit(spec: BaselineSpec) -> EvaluationResult:
    if spec.artifact_id is None and spec.run_id is None:
        raise ValueError("Explicit baseline requires artifact_id or run_id.")
    client = Client()
    if spec.artifact_id is not None:
        artifact = client.get_artifact_version(spec.artifact_id)
        return artifact.load(EvaluationResult)
    raise NotImplementedError(
        "Resolving baseline by run_id is not yet supported. "
        "Pass artifact_id instead."
    )


def _resolve_from_model_registry(
    spec: BaselineSpec,
    suite_name: str,
    mode: EvaluationMode,
) -> Optional[EvaluationResult]:
    """Resolve baseline from the active stack's model registry.

    Stubbed in this task. Wired in Task 7b against the real model-registry
    API (uses production-version + linked-artifact lookup, filtered by
    suite_name and mode).
    """
    client = Client()
    registry = client.get_active_stack().model_registry
    if registry is None:
        logger.debug(
            "No model_registry in active stack; baseline=None "
            "(strategy=model_registry)."
        )
        return None
    logger.warning(
        "Model-registry baseline resolution is stubbed (Task 7b). "
        "Returning None until the real lookup is wired up."
    )
    return None
