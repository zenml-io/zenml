#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Collection of all models concerning assistants."""

from pydantic import Field

from zenml import BaseRequest, BaseResponseBody
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import PluginSubType

# ------------------ Request Model ------------------


class CostAssistantRequest(BaseRequest):
    """BaseModel for all assistant calls."""

    flavor: str = Field(
        title="The flavor of assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    plugin_subtype: PluginSubType = Field(
        title="The plugin subtype of the assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    context: str = Field(
        default="",
        title="The context to pass to the assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    orchestrator: str = Field(
        default="",
        title="The orchestrator to pass to the assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    duration_minutes: str = Field(
        default="60",
        title="The duration to pass to the assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    duration_minutes: str = Field(
        default="60",
        title="The duration to pass to the assistant.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    gpu_type: str = Field(
        default="",
        title="The type of GPU used.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    gpu_amount: str = Field(
        default="",
        title="The amount of GPUs used.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    cpu: str = Field(
        default="",
        title="The number of CPUs.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    memory: str = Field(
        default="",
        title="How much memory.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    location: str = Field(
        default="us-east-1",
        title="The location of the run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    instance_type: str = Field(
        default="n1-standard-4",
        title="The instance type of the run.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
# ------------------ Response Model ------------------


class CostAssistantResponse(BaseResponseBody):
    """ResponseBody for the assistant call."""

    cost: str = Field(
        title="The assistant response.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
