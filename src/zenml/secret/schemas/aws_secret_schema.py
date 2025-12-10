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
"""AWS Authentication Secret Schema definition."""

from typing import Optional

from pydantic import AliasChoices, Field

from zenml.secret.base_secret import BaseSecretSchema


class AWSSecretSchema(BaseSecretSchema):
    """AWS Authentication Secret Schema definition.

    This schema supports both AWS-prefixed field names (for AWS S3) and
    generic field names (for S3-compatible storage like MinIO, Alibaba OSS).

    Supported field names:
        - aws_access_key_id / access_key_id
        - aws_secret_access_key / secret_access_key
        - aws_session_token / session_token
    """

    aws_access_key_id: str = Field(
        validation_alias=AliasChoices("aws_access_key_id", "access_key_id"),
    )
    aws_secret_access_key: str = Field(
        validation_alias=AliasChoices(
            "aws_secret_access_key", "secret_access_key"
        ),
    )
    aws_session_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("aws_session_token", "session_token"),
    )
