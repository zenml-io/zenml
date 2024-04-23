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
"""SQLModel implementation for the server settings table."""

from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class SettingsSchema(SQLModel, table=True):
    """SQL Model for the server settings."""

    __tablename__ = "settings"

    id: UUID = Field(primary_key=True)
    name: str
    email: Optional[str] = Field(nullable=True)
    logo_url: Optional[str] = Field(nullable=True)
    active: bool = Field(default=False)
    enable_analytics: bool = Field(default=False)
    enable_announcements: bool = Field(default=False)
    enable_updates: bool = Field(default=False)
