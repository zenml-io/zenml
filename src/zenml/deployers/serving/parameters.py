#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Shared utilities to construct and validate pipeline parameter models.

This module centralizes the logic to:
- Build a Pydantic model for pipeline parameters from a snapshot
- Validate and normalize request parameters using that model

It is intentionally independent of FastAPI or serving internals so that
other entry points (e.g., CLI) can reuse the same behavior.
"""

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from zenml.logger import get_logger
from zenml.models import PipelineSnapshotResponse
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.utils import source_utils

logger = get_logger(__name__)


def build_params_model_from_snapshot(
    snapshot: PipelineSnapshotResponse,
    *,
    strict: bool = True,
) -> Optional[Type[BaseModel]]:
    """Construct a Pydantic model representing pipeline parameters.

    Load the pipeline class from `pipeline_spec.source` and derive the
    entrypoint signature types to create a dynamic Pydantic model
    (extra='forbid') to use for parameter validation.

    Args:
        snapshot: The snapshot to derive the model from.
        strict: Whether to raise an error if the model cannot be constructed.

    Returns:
        A Pydantic `BaseModel` subclass that validates the pipeline parameters,
        or None if the model could not be constructed.

    Raises:
        RuntimeError: If the model cannot be constructed and `strict` is True.
    """
    if not snapshot.pipeline_spec or not snapshot.pipeline_spec.source:
        msg = (
            f"Snapshot `{snapshot.id}` is missing pipeline_spec.source; "
            "cannot build parameter model."
        )
        if strict:
            raise RuntimeError(msg)
        return None

    try:
        pipeline_class: Pipeline = source_utils.load(
            snapshot.pipeline_spec.source
        )
    except Exception as e:
        logger.debug(f"Failed to load pipeline class from snapshot: {e}")
        if strict:
            raise
        return None

    model = pipeline_class.get_parameters_model()
    if not model:
        message = (
            f"Failed to construct parameters model from pipeline "
            f"`{snapshot.pipeline_configuration.name}`."
        )
        if strict:
            raise RuntimeError(message)
        else:
            logger.debug(message)

    return model


def validate_and_normalize_parameters(
    parameters: Dict[str, Any],
    snapshot: PipelineSnapshotResponse,
    *,
    strict: bool = True,
) -> Dict[str, Any]:
    """Validate and normalize parameters using a Pydantic params model.

    If model construction fails, falls back to merging with snapshot defaults.

    Args:
        parameters: Request parameters.
        snapshot: Snapshot used to derive defaults and the model.
        strict: Whether to raise an error if the model cannot be constructed.

    Returns:
        Validated and normalized parameter dictionary.

    Raises:
        ValueError: If validation fails against the constructed model.
    """
    defaults = (
        (snapshot.pipeline_spec.parameters or {})
        if snapshot.pipeline_spec
        else {}
    )
    merged = {**defaults, **(parameters or {})}

    model = build_params_model_from_snapshot(snapshot, strict=strict)
    if not model:
        if strict:
            raise RuntimeError(
                "Failed to construct parameters model from snapshot."
            )
        return merged

    try:
        inst = model.model_validate(merged)
        return inst.model_dump()
    except Exception as e:  # noqa: BLE001
        # Surface a concise error while keeping details in logs
        logger.debug("Parameter validation error: %s", e)
        raise ValueError(str(e)) from e
