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

from zenml.config.pipeline_configurations import PipelineConfiguration


def test_resolve_step_input_overrides_step_level_only():
    """Tests that step-level overrides apply when no per-invocation override exists."""
    value = uuid4()
    config = PipelineConfiguration(
        name="test",
        step_default_input_overrides={"train": {"data": value}},
    )

    assert config.get_invocation_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": value}
    assert config.get_invocation_input_overrides(
        invocation_id="train_2", step_name="train"
    ) == {"data": value}


def test_resolve_step_input_overrides_per_invocation_only():
    """Tests that per-invocation overrides apply without a step-level override."""
    value = uuid4()
    config = PipelineConfiguration(
        name="test",
        step_input_overrides={"train": {"data": value}},
    )

    assert config.get_invocation_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": value}
    assert (
        config.get_invocation_input_overrides(
            invocation_id="train_2", step_name="train"
        )
        == {}
    )


def test_resolve_step_input_overrides_per_invocation_wins_per_key():
    """Tests that per-invocation overrides win per key over step-level overrides."""
    step_level_data = uuid4()
    step_level_extra = uuid4()
    per_invocation_data = uuid4()
    config = PipelineConfiguration(
        name="test",
        step_default_input_overrides={
            "train": {
                "data": step_level_data,
                "extra": step_level_extra,
            }
        },
        step_input_overrides={"train": {"data": per_invocation_data}},
    )

    assert config.get_invocation_input_overrides(
        invocation_id="train", step_name="train"
    ) == {"data": per_invocation_data, "extra": step_level_extra}


def test_resolve_step_input_overrides_missing_keys():
    """Tests that a missing name or invocation resolves to an empty dict."""
    config = PipelineConfiguration(
        name="test",
        step_default_input_overrides={"train": {"data": uuid4()}},
    )

    assert (
        config.get_invocation_input_overrides(
            invocation_id="train", step_name="other"
        )
        == {}
    )
