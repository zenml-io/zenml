#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Base class for database backup engines."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Generator,
    cast,
)

import pymysql
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import (
    OperationalError,
)
from sqlmodel import create_engine

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration


class BaseDatabaseBackupEngine(ABC):
    """Base class for database backup engines."""

    def __init__(
        self,
        config: "SqlZenStoreConfiguration",
        location: str | None = None,
    ) -> None:
        """Initialize the backup engine.

        Args:
            config: The configuration of the store.
            location: The custom location to store the backup.
        """
        self.config = config
        self._backup_location = location
        url, connect_args, engine_args = config.get_sqlalchemy_config()

        self.url = url
        self.connect_args = connect_args
        self.engine_args = engine_args
        self._engine: Engine | None = None
        self._master_engine: Engine | None = None

    def create_engine(self, database: str | None = None) -> Engine:
        """Get the SQLAlchemy engine for a database.

        Args:
            database: The name of the database. If not set, a master engine
                will be returned.

        Returns:
            The SQLAlchemy engine.
        """
        url = self.url._replace(database=database)
        return create_engine(
            url=url,
            connect_args=self.connect_args,
            **self.engine_args,
        )

    @property
    def engine(self) -> Engine:
        """The SQLAlchemy engine.

        Returns:
            The SQLAlchemy engine.
        """
        if self._engine is None:
            self._engine = self.create_engine(database=self.url.database)
        return self._engine

    @property
    def master_engine(self) -> Engine:
        """The SQLAlchemy engine for the master database.

        Returns:
            The SQLAlchemy engine for the master database.
        """
        if self._master_engine is None:
            self._master_engine = self.create_engine()
        return self._master_engine

    @classmethod
    def is_mysql_missing_database_error(cls, error: OperationalError) -> bool:
        """Checks if the given error is due to a missing database.

        Args:
            error: The error to check.

        Returns:
            If the error because the MySQL database doesn't exist.
        """
        from pymysql.constants.ER import BAD_DB_ERROR

        if not isinstance(error.orig, pymysql.err.OperationalError):
            return False

        error_code = cast(int, error.orig.args[0])
        return error_code == BAD_DB_ERROR

    def database_exists(
        self,
        database: str | None = None,
    ) -> bool:
        """Check if a database exists.

        Args:
            database: The name of the database to check. If not set, the
                database name from the configuration will be used.

        Returns:
            Whether the database exists.

        Raises:
            OperationalError: If connecting to the database failed.
        """
        database = database or self.url.database

        engine = self.create_engine(database=database)
        try:
            engine.connect()
        except OperationalError as e:
            if self.is_mysql_missing_database_error(e):
                return False
            else:
                logger.exception(
                    f"Failed to connect to mysql database `{database}`.",
                )
                raise
        else:
            return True

    def drop_database(
        self,
        database: str | None = None,
    ) -> None:
        """Drops a mysql database.

        Args:
            database: The name of the database to drop. If not set, the
                database name from the configuration will be used.
        """
        database = database or self.url.database
        with self.master_engine.connect() as conn:
            # drop the database if it exists
            logger.info(f"Dropping database '{database}'")
            conn.execute(text(f"DROP DATABASE IF EXISTS `{database}`"))

    def create_database(
        self,
        database: str | None = None,
        drop: bool = False,
    ) -> None:
        """Creates a mysql database.

        Args:
            database: The name of the database to create. If not set, the
                database name from the configuration will be used.
            drop: Whether to drop the database if it already exists.
        """
        database = database or self.url.database
        if drop:
            self.drop_database(database=database)

        with self.master_engine.connect() as conn:
            logger.info(f"Creating database '{database}'")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))

    @abstractmethod
    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.
        """

    @abstractmethod
    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.
        """

    @abstractmethod
    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""

    @property
    def backup_location(self) -> str:
        """The location where the database is backed up to.

        Returns:
            The location where the database is backed up to.

        Raises:
            RuntimeError: If the backup location is not set.
        """
        if self._backup_location is None:
            raise RuntimeError("The backup location is not set.")
        return self._backup_location

    @contextmanager
    def backup_database_context(
        self,
    ) -> Generator[None, Any, Any]:
        """Context manager for backing up and restoring the database.

        Creates a backup before yielding to the caller. If an exception
        occurs during the wrapped operation, the database is restored from
        the backup. If the operation succeeds, the backup is cleaned up.

        Yields:
            None

        Raises:
            RuntimeError: If the wrapped operation fails. The original
                exception is chained.
            Exception: If the wrapped operation fails. The original
                exception is chained.
        """
        logger.info(
            f"Backing up the database before migration to "
            f"`{self.backup_location}`."
        )

        try:
            self.backup_database(overwrite=False)
        except Exception as e:
            raise RuntimeError(
                f"Failed to backup the database: {str(e)}."
            ) from e

        logger.info(
            f"Database successfully backed up to `{self.backup_location}`. If "
            "something goes wrong with the upgrade, ZenML will attempt to "
            "restore the database from this backup automatically."
        )
        try:
            yield
        except Exception:
            logger.info(
                "The database operation failed. Attempting to restore the "
                f"database from `{self.backup_location}`."
            )
            try:
                self.restore_database(cleanup=True)
            except Exception:
                logger.exception(
                    f"Failed to restore the database from "
                    f"`{self.backup_location}`. You might need to restore the "
                    "database manually."
                )
            else:
                logger.info(
                    "The database was successfully restored from "
                    f"`{self.backup_location}`."
                )

            raise

        try:
            self.cleanup_database_backup()
        except Exception:
            logger.exception("Failed to cleanup the database backup.")


class DisabledDatabaseBackupEngine(BaseDatabaseBackupEngine):
    """Database backup engine that is disabled.

    This is used when the backup strategy is set to disabled.
    """

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.

        Raises:
            NotImplementedError: Database backup is not implemented.
        """
        raise NotImplementedError("Database backup is disabled.")

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            NotImplementedError: Database backup is not implemented.
        """
        raise NotImplementedError("Database backup is disabled.")

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup.

        Raises:
            NotImplementedError: Database backup is not implemented.
        """
        raise NotImplementedError("Database backup is disabled.")
