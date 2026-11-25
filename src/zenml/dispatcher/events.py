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
"""Event envelopes dispatched to process-wide event handlers."""

from pydantic import BaseModel, ConfigDict

from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunResponse


class Event(BaseModel):
    """Base class for immutable dispatcher event envelopes."""

    model_config = ConfigDict(frozen=True)


class PipelineRunStatusUpdate(Event):
    """A pipeline run status transition."""

    run: PipelineRunResponse
    previous_status: ExecutionStatus
