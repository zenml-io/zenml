#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import pytest

from zenml.enums import ExecutionStatus
from zenml.orchestrators import publish_utils


def test_publishing_a_successful_step_run(mocker):
    """Tests publishing a successful step run."""
    mock_update_run_step = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.update_run_step",
    )

    step_run_id = uuid4()
    output_artifact_ids = {
        "output_name": [
            uuid4(),
        ]
    }

    publish_utils.publish_successful_step_run(
        step_run_id=step_run_id, output_artifact_ids=output_artifact_ids
    )
    _, call_kwargs = mock_update_run_step.call_args
    assert call_kwargs["step_run_id"] == step_run_id
    assert call_kwargs["step_run_update"].outputs == output_artifact_ids
    assert call_kwargs["step_run_update"].status == ExecutionStatus.COMPLETED


def test_publishing_a_failed_step_run(mocker):
    """Tests publishing a failed step run."""
    mock_update_run_step = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.update_run_step",
    )

    step_run_id = uuid4()

    publish_utils.publish_failed_step_run(step_run_id=step_run_id)
    _, call_kwargs = mock_update_run_step.call_args
    assert call_kwargs["step_run_id"] == step_run_id
    assert call_kwargs["step_run_update"].status == ExecutionStatus.FAILED


def test_publishing_a_failed_pipeline_run(mocker):
    """Tests publishing a failed pipeline run."""
    mock_update_run = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.update_run",
    )

    pipeline_run_id = uuid4()

    publish_utils.publish_failed_pipeline_run(pipeline_run_id=pipeline_run_id)
    _, call_kwargs = mock_update_run.call_args
    assert call_kwargs["run_id"] == pipeline_run_id
    assert call_kwargs["run_update"].status == ExecutionStatus.FAILED


@pytest.mark.parametrize(
    "step_statuses, num_steps, expected_run_status",
    [
        (
            [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED],
            2,
            ExecutionStatus.FAILED,
        ),
        ([ExecutionStatus.COMPLETED], 2, ExecutionStatus.RUNNING),
        (
            [ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING],
            2,
            ExecutionStatus.RUNNING,
        ),
        (
            [ExecutionStatus.COMPLETED, ExecutionStatus.COMPLETED],
            2,
            ExecutionStatus.COMPLETED,
        ),
    ],
)
def test_pipeline_run_status_computation(
    step_statuses, num_steps, expected_run_status
):
    """Tests computing a pipeline run status from step statuses."""
    assert (
        publish_utils.get_pipeline_run_status(
            step_statuses=step_statuses, num_steps=num_steps
        )
        == expected_run_status
    )


def test_publish_pipeline_run_metadata(mocker):
    """Unit test for `publish_pipeline_run_metadata`."""
    mock_create_run = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.create_run_metadata",
    )
    pipeline_run_id = uuid4()
    pipeline_run_metadata = {
        uuid4(): {"key": "value", "key_2": "value_2"},
        uuid4(): {"pi": 3.14},
    }
    publish_utils.publish_pipeline_run_metadata(
        pipeline_run_id=pipeline_run_id,
        pipeline_run_metadata=pipeline_run_metadata,
    )
    assert mock_create_run.call_count == 2  # once per run


def test_publish_step_run_metadata(mocker):
    """Unit test for `publish_step_run_metadata`."""
    mock_create_run = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.create_run_metadata",
    )
    step_run_id = uuid4()
    step_run_metadata = {
        uuid4(): {"key": "value", "key_2": "value_2"},
        uuid4(): {"pi": 3.14},
    }
    publish_utils.publish_step_run_metadata(
        step_run_id=step_run_id,
        step_run_metadata=step_run_metadata,
    )
    assert mock_create_run.call_count == 2  # once per run
