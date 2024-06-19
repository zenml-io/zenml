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

from typing import List
from uuid import UUID

from pydantic import ConfigDict

from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)

# ------------------ Request Model ------------------


class ReportRequest(UserScopedRequest):
    content: str
    persona: str

    model_id: UUID
    model_version_ids: List[UUID]

    model_config = ConfigDict(protected_namespaces=tuple())


# ------------------ Update Model ------------------


class ReportUpdate(BaseUpdate):
    """Update model for service accounts."""

    content: str

    model_config = ConfigDict(validate_assignment=True)


# ------------------ Response Model ------------------


class ReportResponseBody(UserScopedResponseBody):
    content: str
    persona: str
    modified: bool
    model_id: UUID
    model_version_ids: List[UUID]


class ReportResponseMetadata(UserScopedResponseMetadata):
    pass


class ReportResponseResources(UserScopedResponseResources):
    # model: ...
    # model_versions: ...
    pass


class ReportResponse(
    UserScopedResponse[
        ReportResponseBody,
        ReportResponseMetadata,
        ReportResponseResources,
    ]
):
    def get_hydrated_version(self) -> "ReportResponse":
        return self

    # Body and metadata properties
    @property
    def content(self) -> str:
        return self.get_body().content
