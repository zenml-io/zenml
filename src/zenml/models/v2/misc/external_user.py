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
"""Models representing users."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExternalUserModel(BaseModel):
    """External user model."""

    id: UUID
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    is_admin: bool = False
    is_service_account: bool = False
    avatar_url: Optional[str] = None

    model_config = ConfigDict(extra="ignore")
