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
"""SQL schema of the payload blob registry."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Column,
    String,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.schema_utils import build_index

BLOB_SHA256_MEDIA_TYPE_CONSTRAINT = "unique_blob_sha256_media_type"


class BlobSchema(SQLModel, table=True):
    """Registry row of a content-addressed payload blob.

    Blobs are shared by every entity whose payload has the same content, and
    are never updated or deleted. A row only exists once its bytes are
    durable in the backend named by `stored_in`.
    """

    __tablename__ = "blob"
    __table_args__ = (
        UniqueConstraint(
            "sha256", "media_type", name=BLOB_SHA256_MEDIA_TYPE_CONSTRAINT
        ),
        build_index(table_name=__tablename__, column_names=["stored_in"]),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sha256: str = Field(sa_column=Column(String(64), nullable=False))
    media_type: str = Field(sa_column=Column(String(255), nullable=False))
    # How the stored bytes are encoded. Always `identity` for now: the bytes
    # are the UTF-8 encoded payload.
    codec: str = Field(sa_column=Column(String(16), nullable=False))
    size: int = Field(sa_column=Column(BigInteger, nullable=False))
    stored_in: str = Field(sa_column=Column(String(16), nullable=False))
    created: datetime = Field(default_factory=utc_now, nullable=False)
