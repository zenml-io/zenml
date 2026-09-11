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
"""Durable, non-secret submission identity and lifecycle records."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RECEIPT_KEY = "nebius_submission"
IMAGE_KEY = "nebius_step_operator"


class SubmissionReceipt(BaseModel):
    """Recovery information persisted before any cloud mutation.

    This is evidence for one submitter, not a distributed submission lock.
    Secret values and user argv are deliberately excluded.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    revision: int = 0
    component_id: str
    step_run_id: str
    pipeline_run_id: str
    project_id: str
    subnet_id: str
    submission_id: str
    name: str
    image: str
    fingerprint: str
    created_at: float
    deadline: float
    provisioning_deadline: float
    expected_outputs: List[str] = Field(default_factory=list)
    request_timeout: int
    poll_interval: int
    cancel_timeout: int
    publication_grace: int
    operation_id: Optional[str] = None
    job_id: Optional[str] = None
    provider_state: Optional[str] = None
    provider_code: Optional[str] = None
    completion_observed_at: Optional[float] = None
    cancellation_requested: bool = False
    cleanup: Literal["NOT_CONFIRMED", "WORKLOAD_TERMINAL", "UNCONFIRMED"] = (
        "NOT_CONFIRMED"
    )
