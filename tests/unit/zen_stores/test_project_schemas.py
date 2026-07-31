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

import json
from uuid import uuid4

from sqlalchemy.dialects import mysql, postgresql

from zenml.models import ProjectRequest, ProjectUpdate
from zenml.zen_stores.migrations.versions import (
    b53125d4536d_add_project_metadata as migration,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema


def test_project_metadata_column_is_nullable_and_portable() -> None:
    """Tests the column type and rolling-deployment nullability."""
    column = ProjectSchema.__table__.c.project_metadata

    assert (
        column.type.compile(dialect=postgresql.dialect())
        == "VARCHAR(16777215)"
    )
    assert column.type.compile(dialect=mysql.dialect()) == "MEDIUMTEXT"
    assert column.nullable is True
    assert column.server_default is None

    assert (
        migration.PROJECT_METADATA_TYPE.compile(dialect=postgresql.dialect())
        == "VARCHAR(16777215)"
    )
    assert (
        migration.PROJECT_METADATA_TYPE.compile(dialect=mysql.dialect())
        == "MEDIUMTEXT"
    )


def test_project_metadata_serializes_pydantic_supported_types() -> None:
    """Tests metadata serialization for types supported by Pydantic."""
    metadata_id = uuid4()
    schema = ProjectSchema.from_request(
        ProjectRequest(
            name="project-metadata",
            project_metadata={"id": metadata_id},
        )
    )

    assert json.loads(schema.project_metadata or "") == {
        "id": str(metadata_id)
    }

    replacement_id = uuid4()
    schema.update(ProjectUpdate(project_metadata={"id": replacement_id}))

    assert json.loads(schema.project_metadata or "") == {
        "id": str(replacement_id)
    }


def test_project_metadata_defaults_to_empty_dict_for_null_column() -> None:
    """Tests legacy rows with null metadata return an empty dictionary."""
    schema = ProjectSchema.from_request(
        ProjectRequest(name="project-metadata")
    )
    schema.project_metadata = None

    project = schema.to_model(include_metadata=True)

    assert project.project_metadata == {}
