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

from datetime import datetime
from typing import Any, List
from uuid import UUID

from zenml.models import (
    ReportRequest,
    ReportResponse,
    ReportResponseBody,
    ReportResponseMetadata,
    ReportResponseResources,
    ReportUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema


class ReportSchema(BaseSchema, table=True):
    __tablename__ = "report"

    content: str
    persona: str
    modified: bool

    model_id: UUID
    model_version_ids: List[UUID]

    @classmethod
    def from_request(
        cls,
        request: ReportRequest,
    ) -> "ReportSchema":
        now = datetime.utcnow()
        return cls(
            content=request.content,
            persona=request.persona,
            modified=False,
            model_id=request.model_id,
            model_version_ids=request.model_version_ids,
            created=now,
            updated=now,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ReportResponse:
        metadata = None
        if include_metadata:
            metadata = ReportResponseMetadata()

        resources = None
        if include_resources:
            resources = ReportResponseResources()

        body = ReportResponseBody(
            created=self.created,
            updated=self.updated,
            content=self.content,
            model_id=self.model_id,
            model_version_ids=self.model_version_ids,
        )

        return ReportResponse(
            id=self.id, body=body, metadata=metadata, resources=resources
        )

    def update(self, update: ReportUpdate) -> "ReportSchema":
        if self.content != update.content:
            self.modified = True
            self.content = update.content

        self.updated = datetime.utcnow()
        return self
