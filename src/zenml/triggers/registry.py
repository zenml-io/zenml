# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Registry module for type/class trigger resolution."""

from zenml.enums import TriggerType
from zenml.triggers.schedules import (
    ScheduleTriggerRequest,
    ScheduleTriggerResponse,
    ScheduleTriggerResponseBody,
    ScheduleTriggerUpdate,
)

# Type to return class mappings - should be extended with new type classes

TYPE_TO_RESPONSE_BODY_MAPPING = {
    TriggerType.SCHEDULE.value: ScheduleTriggerResponseBody,
}

TYPE_TO_RESPONSE_MAPPING = {
    TriggerType.SCHEDULE.value: ScheduleTriggerResponse,
}

# Union type objects - should be extended with the future type classes (e.g. Webhook)

TRIGGER_UPDATE_TYPE_UNION = ScheduleTriggerUpdate
TRIGGER_CREATE_TYPE_UNION = ScheduleTriggerRequest
TRIGGER_RETURN_TYPE_UNION = ScheduleTriggerResponse
