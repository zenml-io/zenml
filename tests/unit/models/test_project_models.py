#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from datetime import datetime
from uuid import uuid4

import pytest

from zenml.models import (
    ProjectRequest,
    ProjectResponse,
    ProjectResponseBody,
    ProjectResponseMetadata,
    ProjectUpdate,
)


def test_project_metadata_model_contract():
    """Tests nested metadata and omitted versus empty update values."""
    project_metadata = {
        "kitaru": {
            "version": 1,
            "catalog": {"models": [{"name": "classifier"}]},
        }
    }

    request = ProjectRequest(
        name="project-metadata", project_metadata=project_metadata
    )
    assert request.project_metadata == project_metadata
    assert ProjectResponseMetadata().project_metadata == {}
    assert ProjectUpdate().model_dump(exclude_unset=True) == {}
    assert ProjectUpdate(project_metadata={}).model_dump(
        exclude_unset=True
    ) == {"project_metadata": {}}


def test_project_metadata_is_lazily_hydrated(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests that the forwarding property hydrates project metadata lazily."""
    project_id = uuid4()
    now = datetime.now()
    body = ProjectResponseBody(
        created=now,
        updated=now,
        display_name="Project Metadata",
    )
    project_metadata = {"kitaru": {"catalog": {"models": []}}}
    project = ProjectResponse(
        id=project_id,
        name="project-metadata",
        body=body,
    )
    hydrated_project = ProjectResponse(
        id=project_id,
        name="project-metadata",
        body=body,
        metadata=ProjectResponseMetadata(project_metadata=project_metadata),
    )
    monkeypatch.setattr(
        ProjectResponse,
        "get_hydrated_version",
        lambda self: hydrated_project,
    )

    assert project.metadata is None
    assert project.project_metadata == project_metadata
    assert project.metadata is not None
