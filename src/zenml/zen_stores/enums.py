#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Zen Store enums."""

from zenml.utils.enum_utils import StrEnum


class StoreEvent(StrEnum):
    """Events that can be triggered by the store."""

    # Triggered just before deleting a workspace. The workspace ID is passed as
    # a `workspace_id` UUID argument.
    WORKSPACE_DELETED = "workspace_deleted"
    # Triggered just before deleting a user. The user ID is passed as
    # a `user_id` UUID argument.
    USER_DELETED = "user_deleted"
