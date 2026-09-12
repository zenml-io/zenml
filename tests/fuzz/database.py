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
    """Database identity that proves destructive cleanup is test-owned."""

    url: str
    backend: str
    owner: Path
    database_name: Optional[str] = None
    sqlite_path: Optional[Path] = None

    @classmethod
    def sqlite(cls, path: Path, owner: Path) -> "DisposableDatabase":
        """Create an owned SQLite identity.

        Args:
            path: Run-owned database file.
            owner: Run-owned evidence directory.

        Returns:
            The disposable database identity.
        """
        resolved_path = path.resolve()
        return cls(
            url=f"sqlite:///{resolved_path}",
            backend="sqlite",
            owner=owner.resolve(),
            sqlite_path=resolved_path,
        )

    @classmethod
    def mysql(
        cls, url: URL, database_name: str, owner: Path
    ) -> "DisposableDatabase":
        """Create an owned MySQL identity.

        Args:
            url: URL of the uniquely created database.
            database_name: Unique database name assigned to the run.
            owner: Run-owned evidence directory.

        Returns:
            The disposable database identity.
        """
        return cls(
            url=url.render_as_string(hide_password=False),
            backend="mysql",
            owner=owner.resolve(),
            database_name=database_name,
        )

    @classmethod
    def unsafe_for_test(cls, url: str, owner: Path) -> "DisposableDatabase":
        """Construct an untrusted identity for rejection tests.

        Args:
            url: Database URL that must not be treated as disposable.
            owner: Directory presented as the database owner.

        Returns:
            An intentionally unverified database identity.
        """
        return cls(
            url=url, backend=make_url(url).get_backend_name(), owner=owner
        )

    def assert_owned(self) -> None:
        """Reject any database that was not uniquely created for this run.

        Raises:
            RuntimeError: If the database identity is not test-owned.
        """
        if self.backend == "sqlite" and self.sqlite_path is not None:
            path = self.sqlite_path.resolve()
            if (
                path.parent == self.owner.resolve()
                and path.name.startswith("api")
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
    """Small table used only by filter fuzz tests."""

    __tablename__ = "zenml_fuzz_filter_rows"

    id: int = Field(primary_key=True)
    name: Optional[str] = Field(default=None, nullable=True, max_length=512)
    number: Optional[int] = Field(default=None, nullable=True)


@contextmanager
def _evidence_directory() -> Generator[Path, None, None]:
    """Resolve the configured or temporary evidence directory.

    Yields:
        Directory in which fuzz evidence should be written.
    """
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
    """Record non-secret database details used by the fuzz run.

    Args:
        engine: Connected database engine.
        output_directory: Directory in which to write the record.
    """
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
    """Build admin and disposable database details for MySQL.

    Returns:
        The admin engine, disposable database URL, and unique database name.

    Raises:
        RuntimeError: If the configured MySQL service URL is missing or invalid.
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
    admin_url = base_url.set(database=None)
    admin_engine = create_engine(admin_url)
    database_url = base_url.set(database=database_name)
    return admin_engine, database_url, database_name


@contextmanager
def _filter_database(
    output_directory: Path,
) -> Generator[Engine, None, None]:
    """Create and tear down the selected filter fuzz database.

    Args:
        output_directory: Directory in which to place run evidence.

    Yields:
        Engine connected to the disposable database.

    Raises:
        RuntimeError: If the selected backend is unsupported.
    """
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
    """Create and tear down a database owned by this fuzz process.

    Yields:
        Engine connected to the disposable filter database.
    """
    with _evidence_directory() as output_directory:
        with _filter_database(output_directory) as engine:
            yield engine


@contextmanager
def api_database(
    backend: str, output_directory: Path
) -> Generator[DisposableDatabase, None, None]:
    """Create a disposable ZenML server database for API fuzzing.

    Args:
        backend: The selected database backend.
        output_directory: Directory owned by the current fuzz run.

    Yields:
        A verified disposable database identity.

    Raises:
        RuntimeError: If the backend is unsupported or cleanup is unsafe.
    """
    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    if backend == "sqlite":
        path = output_directory / f"api-{os.getpid()}-{token_hex(6)}.sqlite3"
        target = DisposableDatabase.sqlite(path, output_directory)
        target.assert_owned()
        try:
            yield target
        finally:
            target.assert_owned()
            path.unlink(missing_ok=True)
        return
    if backend != "mysql":
        raise RuntimeError("API fuzzing backend must be 'sqlite' or 'mysql'")

    admin_engine, database_url, database_name = _mysql_urls()
    quoted_name = admin_engine.dialect.identifier_preparer.quote(database_name)
    target = DisposableDatabase.mysql(
        database_url, database_name, output_directory
    )
    target.assert_owned()
    created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE {quoted_name} CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci"
                )
            )
        created = True
        yield target
    finally:
        target.assert_owned()
        try:
            if created:
                with admin_engine.begin() as connection:
                    connection.execute(text(f"DROP DATABASE {quoted_name}"))
        finally:
            admin_engine.dispose()
