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
"""Tests for how the store turns step failures into retries."""

import pytest
from sqlmodel import Session

from zenml import pipeline, step
from zenml.client import Client
from zenml.config.retry_config import StepRetryConfig
from zenml.enums import ExecutionStatus
from zenml.models import StepRunUpdate
from zenml.zen_stores.schemas import PipelineRunSchema, StepRunSchema


@step(retry=StepRetryConfig(max_retries=2))
def retriable_step() -> None:
    """Step with retries left after its first attempt."""


@pipeline(enable_cache=False)
def retriable_pipeline() -> None:
    """Pipeline that creates one retriable step run."""
    retriable_step()


@pytest.mark.parametrize(
    "current_status,expected_status",
    [
        (ExecutionStatus.RUNNING, ExecutionStatus.RETRYING),
        (ExecutionStatus.RETRYING, ExecutionStatus.FAILED),
    ],
)
def test_only_first_failure_of_retriable_step_is_retried(
    clean_client: Client,
    current_status: ExecutionStatus,
    expected_status: ExecutionStatus,
) -> None:
    """A step that fails while already retrying is not retried again."""
    run = retriable_pipeline()
    step_run = clean_client.get_pipeline_run(run.id).steps["retriable_step"]

    store = clean_client.zen_store
    with Session(store.engine) as session:
        run_schema = session.get(PipelineRunSchema, run.id)
        run_schema.status = ExecutionStatus.RUNNING.value
        run_schema.in_progress = True
        run_schema.end_time = None
        step_schema = session.get(StepRunSchema, step_run.id)
        step_schema.status = current_status.value
        step_schema.end_time = None
        session.add_all([run_schema, step_schema])
        session.commit()

    updated = store.update_run_step(
        step_run_id=step_run.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
    )

    assert updated.status == expected_status
