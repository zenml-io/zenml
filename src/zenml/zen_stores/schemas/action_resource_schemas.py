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
"""SQL Model Implementations for Action Resources."""
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Relationship

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.trigger_schemas import (
    ActionResourceCompositionSchema,
)

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema


class ActionResourceSchema(BaseSchema, table=True):
    """SQL Model for all action resources."""

    __tablename__ = "action_resource"

    resource_id: UUID
    resource_type: str
    triggers: List["TriggerSchema"] = Relationship(
        back_populates="resources", link_model=ActionResourceCompositionSchema
    )
