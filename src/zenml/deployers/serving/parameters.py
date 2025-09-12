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
- Build a Pydantic model for pipeline parameters from a deployment
- Validate and normalize request parameters using that model

It is intentionally independent of FastAPI or serving internals so that
other entry points (e.g., CLI) can reuse the same behavior.
"""

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ConfigDict, create_model

from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.steps.entrypoint_function_utils import (
    EntrypointFunctionDefinition,
    validate_entrypoint_function,
)
from zenml.utils import source_utils

logger = get_logger(__name__)


def build_params_model_from_deployment(
    deployment: PipelineDeploymentResponse,
    *,
    strict: bool = True,
) -> Optional[Type[BaseModel]]:
    """Construct a Pydantic model representing pipeline parameters.

    Strategy:
    - Load the pipeline class from `pipeline_spec.source` and derive the
      entrypoint signature types to create a dynamic model (extra='forbid').

    Args:
        deployment: The deployment to derive the model from.
        strict: Whether to raise an error if the model cannot be constructed.

    Returns:
        A Pydantic `BaseModel` subclass that validates the pipeline parameters,
        or None if the model could not be constructed.
    """
    try:
        if not deployment.pipeline_spec or not deployment.pipeline_spec.source:
            msg = "Deployment is missing pipeline_spec.source; cannot build parameter model."
            if strict:
                raise RuntimeError(msg)
            return None

        pipeline_class = source_utils.load(deployment.pipeline_spec.source)
        entry_def: EntrypointFunctionDefinition = validate_entrypoint_function(
            pipeline_class.entrypoint
        )

        defaults: Dict[str, Any] = deployment.pipeline_spec.parameters or {}
        fields: Dict[str, tuple] = {}  # type: ignore[type-arg]
        for name, param in entry_def.inputs.items():
            fields[name] = (param.annotation, defaults.get(name, ...))
        model = create_model(
            f"{deployment.pipeline_configuration.name}_ParamsModel",  # type: ignore[arg-type]
            __config__=ConfigDict(extra="forbid"),  # type: ignore[arg-type]
            **fields,  # type: ignore[arg-type]
        )
        return model  # type: ignore[return-value]
    except Exception as e:
        logger.debug("Failed to build params model from deployment: %s", e)
        if strict:
            raise
        return None


def validate_and_normalize_parameters(
    parameters: Dict[str, Any],
    deployment: PipelineDeploymentResponse,
    *,
    strict: bool = True,
) -> Dict[str, Any]:
    """Validate and normalize parameters using a Pydantic params model.

    If model construction fails, falls back to merging with deployment defaults.

    Args:
        parameters: Request parameters.
        deployment: Deployment used to derive defaults and the model.
        strict: Whether to raise an error if the model cannot be constructed.

    Returns:
        Validated and normalized parameter dictionary.

    Raises:
        ValueError: If validation fails against the constructed model.
    """
    defaults = (
        (deployment.pipeline_spec.parameters or {})
        if deployment.pipeline_spec
        else {}
    )
    merged = {**defaults, **(parameters or {})}

    model = build_params_model_from_deployment(deployment, strict=strict)
    if not model:
        if strict:
            raise RuntimeError(
                "Failed to construct parameters model from deployment."
            )
        return merged

    try:
        inst = model.model_validate(merged)
        return inst.model_dump()
    except Exception as e:  # noqa: BLE001
        # Surface a concise error while keeping details in logs
        logger.debug("Parameter validation error: %s", e)
        raise ValueError(str(e)) from e
