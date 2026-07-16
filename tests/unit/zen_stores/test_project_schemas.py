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

from sqlalchemy.dialects import mysql, postgresql

from zenml.zen_stores.migrations.versions import (
    b53125d4536d_add_project_metadata as migration,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema


def test_project_metadata_column_is_portable_and_has_server_default() -> None:
    """Tests portable column types and rolling-deployment defaults."""
    column = ProjectSchema.__table__.c.project_metadata

    assert column.type.compile(dialect=postgresql.dialect()) == "TEXT"
    assert column.type.compile(dialect=mysql.dialect()) == "MEDIUMTEXT"
    assert column.nullable is False
    assert str(column.server_default.arg) == "('{}')"

    assert (
        migration.PROJECT_METADATA_TYPE.compile(dialect=postgresql.dialect())
        == "TEXT"
    )
    assert (
        migration.PROJECT_METADATA_TYPE.compile(dialect=mysql.dialect())
        == "MEDIUMTEXT"
    )
    assert str(migration.PROJECT_METADATA_DEFAULT) == "('{}')"
