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
from uuid import uuid4

from zenml.config.execution_overrides import ExecutionOverrides
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import ArtifactVersionInputSource
from zenml.models import PipelineSnapshotBase


def test_get_input_overrides_step_level_only():
    """Tests that step-level overrides apply when no per-invocation override exists."""
    source = ArtifactVersionInputSource(id=uuid4())
    overrides = ExecutionOverrides(
        default_input_overrides={"train": {"data": source}},
    )

    assert overrides.get_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": source}
    assert overrides.get_input_overrides(
        invocation_id="train_2", step_name="train"
    ) == {"data": source}


def test_get_input_overrides_per_invocation_only():
    """Tests that per-invocation overrides apply without a step-level override."""
    source = ArtifactVersionInputSource(id=uuid4())
    overrides = ExecutionOverrides(
        input_overrides={"train": {"data": source}},
    )

    assert overrides.get_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": source}
    assert (
        overrides.get_input_overrides(
            invocation_id="train_2", step_name="train"
        )
        == {}
    )


def test_get_input_overrides_per_invocation_wins_per_key():
    """Tests that per-invocation overrides win per key over step-level overrides."""
    step_level_data = ArtifactVersionInputSource(id=uuid4())
    step_level_extra = ArtifactVersionInputSource(id=uuid4())
    per_invocation_data = ArtifactVersionInputSource(id=uuid4())
    overrides = ExecutionOverrides(
        default_input_overrides={
            "train": {
                "data": step_level_data,
                "extra": step_level_extra,
            }
        },
        input_overrides={"train": {"data": per_invocation_data}},
    )

    assert overrides.get_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": per_invocation_data, "extra": step_level_extra}


def test_get_input_overrides_missing_keys():
    """Tests that a missing name or invocation resolves to an empty dict."""
    overrides = ExecutionOverrides(
        default_input_overrides={
            "train": {"data": ArtifactVersionInputSource(id=uuid4())}
        },
    )

    assert (
        overrides.get_input_overrides(invocation_id="train", step_name="other")
        == {}
    )


def test_snapshot_migrates_legacy_execution_overrides():
    """Tests that legacy pipeline configuration fields are migrated."""
    artifact_version_id = uuid4()
    snapshot = PipelineSnapshotBase(
        run_name_template="run",
        pipeline_configuration=PipelineConfiguration(
            name="test",
            steps_to_skip={"train"},
            skip_successful_steps=True,
            step_input_overrides={"train_2": {"data": artifact_version_id}},
        ),
    )

    assert snapshot.execution_overrides == ExecutionOverrides(
        steps_to_skip={"train"},
        skip_successful_steps=True,
        input_overrides={
            "train_2": {
                "data": ArtifactVersionInputSource(id=artifact_version_id)
            }
        },
    )
    assert not snapshot.pipeline_configuration.steps_to_skip
    assert not snapshot.pipeline_configuration.skip_successful_steps
    assert not snapshot.pipeline_configuration.step_input_overrides


def test_snapshot_without_legacy_execution_overrides():
    """Tests that snapshots without legacy fields keep their overrides."""
    overrides = ExecutionOverrides(steps_to_skip={"train"})
    snapshot = PipelineSnapshotBase(
        run_name_template="run",
        pipeline_configuration=PipelineConfiguration(name="test"),
        execution_overrides=overrides,
    )

    assert snapshot.execution_overrides == overrides
