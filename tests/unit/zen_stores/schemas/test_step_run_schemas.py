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
"""Unit tests for step run schemas."""

from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus
from zenml.models import StepRunUpdate
from zenml.zen_stores.schemas import StepRunSchema

CACHE_EXPIRES_AT = datetime(2026, 1, 1)


@pytest.mark.parametrize(
    ("step_run_update", "affects_run_status"),
    [
        (StepRunUpdate(), True),
        (StepRunUpdate(cache_expires_at=CACHE_EXPIRES_AT), False),
        (StepRunUpdate(cache_expires_at=None), False),
        (
            StepRunUpdate(
                outputs={"output": [uuid4()]},
                loaded_artifact_versions={"input": uuid4()},
            ),
            False,
        ),
        (StepRunUpdate(add_logs=[]), False),
        (StepRunUpdate(status=ExecutionStatus.COMPLETED), True),
        (
            StepRunUpdate(
                status=ExecutionStatus.COMPLETED,
                cache_expires_at=CACHE_EXPIRES_AT,
            ),
            True,
        ),
        (StepRunUpdate(status=None, cache_expires_at=CACHE_EXPIRES_AT), True),
        (
            StepRunUpdate(exception_info=None, outputs={"output": [uuid4()]}),
            True,
        ),
    ],
    ids=[
        "empty",
        "cache-expiration",
        "cache-expiration-none",
        "artifacts",
        "logs",
        "status",
        "status-and-cache-expiration",
        "status-none-and-cache-expiration",
        "exception-info-none-and-outputs",
    ],
)
def test_step_run_update_affects_run_status(
    step_run_update: StepRunUpdate, affects_run_status: bool
) -> None:
    """Tests which step run updates can affect the status of their run."""
    assert (
        StepRunSchema.update_affects_run_status(step_run_update)
        is affects_run_status
    )

    # The REST store sends every field that was set, including `None` values,
    # so the server has to come to the same result.
    sent_update = StepRunUpdate.model_validate(
        step_run_update.model_dump(mode="json", exclude_unset=True)
    )
    assert (
        StepRunSchema.update_affects_run_status(sent_update)
        is affects_run_status
    )
