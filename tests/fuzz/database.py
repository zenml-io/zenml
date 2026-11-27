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
"""Disposable SQLModel database lifecycle for generated fuzz tests."""

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from secrets import token_hex
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlmodel import Field, SQLModel

TEST_DATABASE_PREFIX = "zenml_fuzz_"


@dataclass(frozen=True)
class DisposableDatabase:
    """Identity of a run-owned SQLite file or disposable MySQL database."""

    url: str
    backend: str
    owner: Path
    database_name: Optional[str] = None
    sqlite_path: Optional[Path] = None

    def assert_owned(self) -> None:
        """Refuse destructive cleanup on any database not created by this run.

        Raises:
            RuntimeError: If the database identity is not test-owned.
        """
        if self.backend == "sqlite" and self.sqlite_path is not None:
            path = self.sqlite_path.resolve()
            if (
                path.parent == self.owner.resolve()
                and path.name.startswith("api-")
                and make_url(self.url).database == str(path)
            ):
                return
        elif self.backend == "mysql" and self.database_name is not None:
            if (
                self.database_name.startswith(TEST_DATABASE_PREFIX)
                and make_url(self.url).database == self.database_name
            ):
                return
        raise RuntimeError(
            f"Database URL is not a disposable fuzz database: {self.backend}"
        )


class FilterRow(SQLModel, table=True):
    """Small table used by SQL filter oracle fuzz tests."""

    __tablename__ = "zenml_fuzz_filter_rows"

    id: int = Field(primary_key=True)
    name: Optional[str] = Field(default=None, nullable=True, max_length=512)
    number: Optional[int] = Field(default=None, nullable=True)


@contextmanager
def _evidence_directory() -> Generator[Path, None, None]:
    """Yield the configured evidence directory or a temporary fallback."""
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
    """Record non-secret database metadata for reproduction."""
    configuration = {
        "backend": os.environ.get("ZENML_FUZZ_BACKEND", "sqlite"),
        "dialect": engine.dialect.name,
        "driver": engine.dialect.driver,
        "server_version": list(engine.dialect.server_version_info or ()),
        "url": engine.url.render_as_string(hide_password=True),
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
    """Build admin engine, unique database URL, and database name for MySQL.

    Returns:
        Tuple of ``(admin_engine, database_url, database_name)``.

    Raises:
        RuntimeError: If ``ZENML_FUZZ_MYSQL_URL`` is missing or non-MySQL.
    """
    configured = os.environ.get("ZENML_FUZZ_MYSQL_URL")
    if not configured:
        raise RuntimeError(
            "ZENML_FUZZ_MYSQL_URL must identify the disposable MySQL service"
        )
    base_url = make_url(configured)
    if base_url.get_backend_name() != "mysql":
        raise RuntimeError("ZENML_FUZZ_MYSQL_URL must use a MySQL dialect")
    database_name = f"{TEST_DATABASE_PREFIX}{os.getpid()}_{token_hex(6)}"
    admin_engine = create_engine(base_url.set(database=None))
    return admin_engine, base_url.set(database=database_name), database_name


@contextmanager
def _disposable_mysql_database() -> Generator[tuple[URL, str], None, None]:
    """Create and always drop one uniquely named MySQL database.

    Uses the MySQL server's default charset and collation (``utf8mb4_0900_ai_ci``
    on MySQL 8.0), matching real ZenML deployments instead of forcing a binary
    collation.

    Yields:
        Tuple of ``(database_url, database_name)``.
    """
    admin_engine, database_url, database_name = _mysql_urls()
    assert database_name.startswith(TEST_DATABASE_PREFIX)
    quoted_name = admin_engine.dialect.identifier_preparer.quote(database_name)
    created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f"CREATE DATABASE {quoted_name}"))
        created = True
        yield database_url, database_name
    finally:
        try:
            if created:
                with admin_engine.begin() as connection:
                    connection.execute(
                        text(f"DROP DATABASE IF EXISTS {quoted_name}")
                    )
        finally:
            admin_engine.dispose()


@contextmanager
def filter_database() -> Generator[Engine, None, None]:
    """Create and tear down a disposable SQL engine for filter fuzzing.

    Yields:
        Connected SQLAlchemy engine with ``FilterRow`` created.

    Raises:
        RuntimeError: If ``ZENML_FUZZ_BACKEND`` is unsupported.
    """
    backend = os.environ.get("ZENML_FUZZ_BACKEND", "sqlite")
    with _evidence_directory() as output_directory:
        if backend == "sqlite":
            sqlite_path = output_directory / f"filters-{os.getpid()}.sqlite3"
            engine = create_engine(f"sqlite:///{sqlite_path}")
            try:
                FilterRow.__table__.create(  # type: ignore[attr-defined]
                    engine, checkfirst=False
                )
                _record_configuration(engine, output_directory)
                yield engine
            finally:
                engine.dispose()
                sqlite_path.unlink(missing_ok=True)
            return

        if backend != "mysql":
            raise RuntimeError(
                "ZENML_FUZZ_BACKEND must be either 'sqlite' or 'mysql'"
            )

        with _disposable_mysql_database() as (database_url, _database_name):
            engine = create_engine(database_url, pool_pre_ping=True)
            try:
                FilterRow.__table__.create(  # type: ignore[attr-defined]
                    engine, checkfirst=False
                )
                _record_configuration(engine, output_directory)
                yield engine
            finally:
                engine.dispose()


@contextmanager
def api_database(
    backend: str, output_directory: Path
) -> Generator[DisposableDatabase, None, None]:
    """Create and tear down a disposable database for the API fuzz server.

    Args:
        backend: Selected backend (``sqlite`` or ``mysql``).
        output_directory: Run-owned evidence directory.

    Yields:
        Verified disposable database identity.

    Raises:
        RuntimeError: If ``backend`` is unsupported.
    """
    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    if backend == "sqlite":
        path = (
            output_directory / f"api-{os.getpid()}-{token_hex(6)}.sqlite3"
        ).resolve()
        target = DisposableDatabase(
            url=f"sqlite:///{path}",
            backend="sqlite",
            owner=output_directory,
            sqlite_path=path,
        )
        target.assert_owned()
        try:
            yield target
        finally:
            target.assert_owned()
            path.unlink(missing_ok=True)
        return

    if backend != "mysql":
        raise RuntimeError("API fuzzing backend must be 'sqlite' or 'mysql'")

    with _disposable_mysql_database() as (database_url, database_name):
        target = DisposableDatabase(
            url=database_url.render_as_string(hide_password=False),
            backend="mysql",
            owner=output_directory,
            database_name=database_name,
        )
        target.assert_owned()
        yield target
