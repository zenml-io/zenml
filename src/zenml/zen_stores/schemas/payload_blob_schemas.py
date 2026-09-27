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

PAYLOAD_BLOB_SHA256_CONSTRAINT = "unique_payload_blob_sha256"
LOCATION_FINGERPRINT_LENGTH = 16


class PayloadBlobSchema(SQLModel, table=True):
    """Registry row of a content-addressed payload blob.

    Blobs are shared by every entity whose payload has the same content, and
    are never updated or deleted. A row only exists once its bytes are
    durable at the location that `location_fingerprint` identifies: the backend and a
    digest of its path, such as `s3:6de5d6037f732`.
    """

    __tablename__ = "payload_blob"
    __table_args__ = (
        UniqueConstraint("sha256", name=PAYLOAD_BLOB_SHA256_CONSTRAINT),
        build_index(
            table_name=__tablename__, column_names=["location_fingerprint"]
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sha256: str = Field(sa_column=Column(String(64), nullable=False))
    # How the stored bytes are encoded. Always `identity` for now: the bytes
    # are the UTF-8 encoded payload.
    codec: str = Field(sa_column=Column(String(16), nullable=False))
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    location_fingerprint: str = Field(
        sa_column=Column(String(LOCATION_FINGERPRINT_LENGTH), nullable=False)
    )
    created: datetime = Field(default_factory=utc_now, nullable=False)
