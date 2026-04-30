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

import json
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

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
    # When strategy="model_registry": if model_version_id is set it is used
    # directly; otherwise model_name is required to locate the production
    # version via get_latest_model_version.
    model_version_id: Optional[UUID] = None
    model_name: Optional[str] = Field(
        None,
        description="Name of the registered model. Required when model_version_id is not "
        "set; used to look up the production version via the model registry. "
        "Ignored when model_version_id is provided.",
    )


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

    When spec.model_version_id is provided it is used directly. Otherwise
    spec.model_name is required and get_latest_model_version(name,
    stage=PRODUCTION) is called to locate the current production version.

    Linked artifact versions are retrieved via
    Client().list_artifact_versions(model_version_id=...). Because the
    materializer persists suite_name/mode inside the JSON body (not as
    ZenML artifact metadata), each candidate must be loaded and inspected.
    The list is iterated in the order the API returns it (default sort is
    ascending by created); the last matching artifact is returned as the
    most recently produced baseline.

    API surface used:
      - BaseModelRegistry.get_latest_model_version(name, stage) -> Optional[RegistryModelVersion]
      - Client().list_artifact_versions(model_version_id=UUID) -> Page[ArtifactVersionResponse]
      - ArtifactVersionResponse.load() -> Any
    """
    from zenml.model_registries.base_model_registry import ModelVersionStage

    client = Client()
    registry = client.get_active_stack().model_registry
    if registry is None:
        logger.debug(
            "No model_registry in active stack; baseline=None "
            "(strategy=model_registry)."
        )
        return None

    version_id = spec.model_version_id
    if version_id is None:
        if not spec.model_name:
            logger.debug(
                "model_registry strategy requires model_name (or "
                "model_version_id) in BaselineSpec; baseline=None."
            )
            return None
        prod_version = registry.get_latest_model_version(
            name=spec.model_name,
            stage=ModelVersionStage.PRODUCTION,
        )
        if prod_version is None:
            logger.debug(
                "No production model version for model '%s'; baseline=None.",
                spec.model_name,
            )
            return None
        version_id = prod_version.id

    candidates = client.list_artifact_versions(
        model_version_id=version_id,
    )

    # Load each candidate and filter by suite_name / mode. The materializer
    # stores these fields inside the JSON body, not as ZenML artifact
    # metadata, so we must deserialize to inspect them.
    latest: Optional[EvaluationResult] = None
    for art in candidates:
        try:
            result = art.load()
        except (
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
            json.JSONDecodeError,
        ):
            logger.debug(
                "Failed to load artifact %s; skipping.", art.id, exc_info=True
            )
            continue
        if not isinstance(result, EvaluationResult):
            continue
        if result.suite_name == suite_name and result.mode == mode:
            latest = result

    if latest is None:
        logger.debug(
            "No EvaluationResult artifact matched suite_name=%r mode=%r "
            "in model version %s.",
            suite_name,
            mode,
            version_id,
        )
    return latest
