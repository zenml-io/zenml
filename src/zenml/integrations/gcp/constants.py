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
"""Constants for the VertexAI integration."""

from google.cloud.aiplatform_v1.types.job_state import JobState

VERTEX_ENDPOINT_SUFFIX = "-aiplatform.googleapis.com"
POLLING_INTERVAL_IN_SECONDS = 30
CONNECTION_ERROR_RETRY_LIMIT = 5
_VERTEX_JOB_STATE_SUCCEEDED = JobState.JOB_STATE_SUCCEEDED
_VERTEX_JOB_STATE_FAILED = JobState.JOB_STATE_FAILED
_VERTEX_JOB_STATE_CANCELLED = JobState.JOB_STATE_CANCELLED

VERTEX_JOB_STATES_COMPLETED = (
    _VERTEX_JOB_STATE_SUCCEEDED,
    _VERTEX_JOB_STATE_FAILED,
    _VERTEX_JOB_STATE_CANCELLED,
)
VERTEX_JOB_STATES_FAILED = (
    _VERTEX_JOB_STATE_FAILED,
    _VERTEX_JOB_STATE_CANCELLED,
)

GKE_ACCELERATOR_NODE_SELECTOR_CONSTRAINT_LABEL = (
    "cloud.google.com/gke-accelerator"
)
