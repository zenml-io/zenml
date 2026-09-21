# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Decode run substitutions and merge stored step definitions."""

import json
from datetime import datetime
from typing import Optional

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step


def run_pipeline_configuration(
    configuration: str, start_time: Optional[datetime]
) -> PipelineConfiguration:
    """Resolve a stored pipeline's substitutions for one execution.

    Args:
        configuration: Serialized pipeline configuration.
        start_time: Recorded execution start, or the live reader's clock fallback.

    Returns:
        Parsed pipeline configuration with finalized substitutions.
    """
    pipeline = PipelineConfiguration.model_validate_json(configuration)
    pipeline.finalize_substitutions(start_time=start_time, inplace=True)
    return pipeline


def merge_step_configuration(
    configuration: str,
    pipeline: PipelineConfiguration,
    *,
    exclude_hook_sources: bool,
) -> Step:
    """Merge one stored definition without mutating shared pipeline values.

    Args:
        configuration: Serialized static or dynamic step definition.
        pipeline: Pipeline configuration with the caller's substitution context.
        exclude_hook_sources: Existing dynamic-pipeline hook deserialization policy.

    Returns:
        Independent step configuration with pipeline defaults applied.
    """
    return Step.from_dict(
        json.loads(configuration),
        pipeline_configuration=pipeline.model_copy(deep=True),
        exclude_hook_sources=exclude_hook_sources,
    )
