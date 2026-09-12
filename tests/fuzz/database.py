#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Disposable SQLModel database lifecycle for generated tests."""

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from secrets import token_hex
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlmodel import Field, SQLModel


class FilterRow(SQLModel, table=True):
    """Small table used only by filter fuzz tests."""

    __tablename__ = "zenml_fuzz_filter_rows"

    id: int = Field(primary_key=True)
    name: Optional[str] = Field(default=None, nullable=True, max_length=512)
    number: Optional[int] = Field(default=None, nullable=True)


@contextmanager
def _evidence_directory() -> Generator[Path, None, None]:
    configured = os.environ.get("ZENML_FUZZ_OUTPUT_DIR")
    if configured:
        path = Path(configured)
        path.mkdir(parents=True, exist_ok=True)
        yield path
        return
    with tempfile.TemporaryDirectory(
        prefix="zenml-fuzz-evidence-"
    ) as directory:
        yield Path(directory)


def _record_configuration(engine: Engine, output_directory: Path) -> None:
    engine_url = engine.url.render_as_string(hide_password=True)
    configuration = {
        "backend": os.environ.get("ZENML_FUZZ_BACKEND", "sqlite"),
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
        "server_version": list(engine.dialect.server_version_info or ()),
        "url": engine_url,
    }
    if engine.dialect.name == "mysql":
        with engine.connect() as connection:
            configuration["collation"] = connection.execute(
                text("SELECT @@collation_database")
            ).scalar_one()
    else:
        configuration["collation"] = "BINARY (default SQLite comparison)"
    (output_directory / "database.json").write_text(
        json.dumps(configuration, indent=2, sort_keys=True) + "\n"
    )


def _mysql_urls() -> tuple[Engine, URL, str]:
    configured = os.environ.get("ZENML_FUZZ_MYSQL_URL")
    if not configured:
        raise RuntimeError(
            "ZENML_FUZZ_MYSQL_URL must identify the disposable MySQL service"
        )
    base_url = make_url(configured)
    if base_url.get_backend_name() != "mysql":
        raise RuntimeError("ZENML_FUZZ_MYSQL_URL must use a MySQL dialect")

    database_name = f"zenml_fuzz_{os.getpid()}_{token_hex(6)}"
    admin_url = base_url.set(database=None)
    admin_engine = create_engine(admin_url)
    database_url = base_url.set(database=database_name)
    return admin_engine, database_url, database_name


@contextmanager
def _filter_database(
    output_directory: Path,
) -> Generator[Engine, None, None]:
    backend = os.environ.get("ZENML_FUZZ_BACKEND", "sqlite")
    admin_engine: Optional[Engine] = None
    database_name: Optional[str] = None
    sqlite_path: Optional[Path] = None

    if backend == "sqlite":
        sqlite_path = output_directory / f"filters-{os.getpid()}.sqlite3"
        engine = create_engine(f"sqlite:///{sqlite_path}")
    elif backend == "mysql":
        admin_engine, database_url, database_name = _mysql_urls()
        quoted_name = admin_engine.dialect.identifier_preparer.quote(
            database_name
        )
        with admin_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE {quoted_name} CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci"
                )
            )
        engine = create_engine(database_url, pool_pre_ping=True)
    else:
        raise RuntimeError(
            "ZENML_FUZZ_BACKEND must be either 'sqlite' or 'mysql'"
        )

    try:
        FilterRow.__table__.create(  # type: ignore[attr-defined]
            engine, checkfirst=False
        )
        with engine.connect():
            pass
        _record_configuration(engine, output_directory)
        yield engine
    finally:
        engine.dispose()
        if admin_engine is not None and database_name is not None:
            quoted_name = admin_engine.dialect.identifier_preparer.quote(
                database_name
            )
            with admin_engine.begin() as connection:
                connection.execute(text(f"DROP DATABASE {quoted_name}"))
            admin_engine.dispose()
        elif sqlite_path is not None:
            sqlite_path.unlink(missing_ok=True)


@contextmanager
def filter_database() -> Generator[Engine, None, None]:
    """Create and tear down a database owned by this fuzz process."""
    with _evidence_directory() as output_directory:
        with _filter_database(output_directory) as engine:
            yield engine
