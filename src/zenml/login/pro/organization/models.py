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
"""ZenML Pro organization models."""

from datetime import datetime
from uuid import UUID

from zenml.login.pro.models import BaseRestAPIModel


class OrganizationRead(BaseRestAPIModel):
    """Model for viewing organizations."""

    id: UUID

    name: str
    description: str | None = None

    created: datetime
    updated: datetime
