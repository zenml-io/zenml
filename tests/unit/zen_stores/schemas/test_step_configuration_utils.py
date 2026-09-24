# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Tests for merging stored step definitions with their pipeline."""

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import (
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.zen_stores.schemas.step_configuration_utils import (
    merge_step_configuration,
)


def stored_definition(name: str, substitutions: dict[str, str]) -> str:
    """Serialize a step definition the way a snapshot stores it."""
    return Step(
        spec=StepSpec(
            source=Source(
                module="tests", attribute=name, type=SourceType.INTERNAL
            ),
            upstream_steps=[],
        ),
        config=StepConfiguration(name=name, substitutions=substitutions),
    ).model_dump_json()


def test_one_step_substitutions_do_not_reach_the_next_step() -> None:
    """Steps merged against one pipeline configuration stay independent."""
    pipeline = PipelineConfiguration(
        name="pipeline", substitutions={"owner": "pipeline"}
    )

    first = merge_step_configuration(
        stored_definition("first", {"owner": "first", "extra": "1"}),
        pipeline,
        exclude_hook_sources=False,
    )
    second = merge_step_configuration(
        stored_definition("second", {}),
        pipeline,
        exclude_hook_sources=False,
    )

    assert first.config.substitutions == {"owner": "first", "extra": "1"}
    assert second.config.substitutions == {"owner": "pipeline"}
    assert pipeline.substitutions == {"owner": "pipeline"}
