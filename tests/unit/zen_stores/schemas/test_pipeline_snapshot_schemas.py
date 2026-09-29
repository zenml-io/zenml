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
"""Tests for converting stored pipeline snapshots to response models."""

from typing import List, Optional
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.zen_stores import template_utils
from zenml.zen_stores.schemas import (
    PipelineBuildSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
)


@pytest.mark.parametrize("step_filter", [None, ["second"]])
def test_snapshot_step_substitutions_stay_independent(
    monkeypatch: pytest.MonkeyPatch,
    step_filter: Optional[List[str]],
) -> None:
    """Legacy step overrides do not leak into snapshots or sibling steps."""
    snapshot = PipelineSnapshotSchema(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        pipeline_configuration=PipelineConfiguration(
            name="pipeline", substitutions={"owner": "pipeline"}
        ).model_dump_json(),
        client_environment="{}",
        run_name_template="pipeline",
        step_count=2,
        build=PipelineBuildSchema(
            stack_id=uuid4(),
            is_local=False,
            images="{}",
            contains_code=True,
            zenml_version=None,
            python_version=None,
            checksum=None,
            stack_checksum=None,
        ),
    )
    definitions = [
        StepConfigurationSchema(
            name=name,
            index=index,
            snapshot_id=snapshot.id,
            config=Step(
                spec=StepSpec(
                    source=Source(
                        module="tests",
                        attribute=name,
                        type=SourceType.INTERNAL,
                    ),
                    upstream_steps=[],
                    invocation_id=name,
                ),
                config=StepConfiguration(
                    name=name, substitutions=substitutions
                ),
                step_config_overrides=StepConfiguration(
                    name=name, substitutions=substitutions
                ),
            ).model_dump_json(),
        )
        for index, (name, substitutions) in enumerate(
            [("first", {"owner": "first", "extra": "1"}), ("second", {})]
        )
    ]
    monkeypatch.setattr(
        PipelineSnapshotSchema,
        "get_step_configurations",
        lambda self, include=None: [
            definition
            for definition in definitions
            if not include or definition.name in include
        ],
    )
    generate_schema = Mock(return_value=None)
    monkeypatch.setattr(
        template_utils, "generate_config_schema", generate_schema
    )
    monkeypatch.setattr(
        template_utils, "generate_config_template", Mock(return_value=None)
    )

    response = snapshot.to_model(
        include_metadata=True,
        include_config_schema=True,
        step_configuration_filter=step_filter,
    )

    assert response.pipeline_configuration.substitutions == {
        "owner": "pipeline"
    }
    assert response.step_configurations["second"].config.substitutions == {
        "owner": "pipeline"
    }
    schema_steps = generate_schema.call_args.kwargs["step_configurations"]
    assert schema_steps["first"].config.substitutions == {
        "owner": "first",
        "extra": "1",
    }
    assert schema_steps["second"].config.substitutions == {"owner": "pipeline"}
