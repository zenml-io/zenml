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
"""Basic Authentication Secret Schema definition."""

from zenml.secret.base_secret import BaseSecretSchema


class BasicAuthSecretSchema(BaseSecretSchema):
    """Secret schema for basic authentication.

    Attributes:
        username: The username that should be used for authentication.
        password: The password that should be used for authentication.
    """

    username: str
    password: str
