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
"""JSON database backup engine."""

import datetime
import json
import os
import re
import shutil
import uuid
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Generator,
    TextIO,
)

from sqlalchemy import Engine, MetaData, func, text
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlmodel import (
    select,
)

from zenml.logger import get_logger
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.migrations.backup.base import BaseDatabaseBackupEngine

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration


class SQLAlchemyDatabaseBackupEngine(BaseDatabaseBackupEngine):
    """Base class for SQLAlchemy-based database backup engines."""

    def backup_database_to_storage(
        self,
        **store_db_kwargs: Any,
    ) -> None:
        """Backup the database to a storage location.

        Backup the database to an abstract storage location. The storage
        location is implemented by the `store_database_data` method that is
        called repeatedly to store the database information.

        Args:
            store_db_kwargs: Additional keyword arguments to pass to the
                `store_database_data` method.
        """
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        with self.engine.connect() as conn:
            for table in metadata.sorted_tables:
                # 1. extract the table creation statements

                create_table_construct = CreateTable(table)
                create_table_stmt = str(create_table_construct).strip()
                for column in create_table_construct.columns:
                    # enclosing all column names in backticks. This is because
                    # some column names are reserved keywords in MySQL. For
                    # example, keys and values. So, instead of tracking all
                    # keywords, we just enclose all column names in backticks.
                    # enclose the first word in the column definition in
                    # backticks
                    words = str(column).split()
                    words[0] = f"`{words[0]}`"
                    create_table_stmt = create_table_stmt.replace(
                        f"\n\t{str(column)}", " ".join(words)
                    )
                # if any double quotes are used for column names, replace them
                # with backticks
                create_table_stmt = create_table_stmt.replace('"', "") + ";"

                # enclose all table names in backticks. This is because some
                # table names are reserved keywords in MySQL (e.g key
                # and trigger).
                create_table_stmt = create_table_stmt.replace(
                    f"CREATE TABLE {table.name}",
                    f"CREATE TABLE `{table.name}`",
                )
                # do the same for references to other tables
                # (i.e. foreign key constraints) by replacing REFERENCES <word>
                # with REFERENCES `<word>`
                # use a regular expression for this
                create_table_stmt = re.sub(
                    r"REFERENCES\s+(\w+)",
                    r"REFERENCES `\1`",
                    create_table_stmt,
                )

                # In SQLAlchemy, the CreateTable statement may not always
                # include unique constraints explicitly if they are implemented
                # as unique indexes instead. To make sure we get all unique
                # constraints, including those implemented as indexes, we
                # extract the unique constraints from the table schema and add
                # them to the create table statement.

                # Extract the unique constraints from the table schema
                index_create_statements = []
                unique_constraints = []
                for index in table.indexes:
                    if index.unique:
                        unique_columns = [
                            f"`{column.name}`" for column in index.columns
                        ]
                        unique_constraints.append(
                            f"UNIQUE KEY `{index.name}` ({', '.join(unique_columns)})"
                        )
                    else:
                        if index.name in {
                            fk.name for fk in table.foreign_key_constraints
                        }:
                            # Foreign key indices are already handled by the
                            # table creation statement.
                            continue

                        index_create = str(CreateIndex(index)).strip()
                        index_create = index_create.replace(
                            f"CREATE INDEX {index.name}",
                            f"CREATE INDEX `{index.name}`",
                        )
                        index_create = index_create.replace(
                            f"ON {table.name}", f"ON `{table.name}`"
                        )

                        for column_name in index.columns.keys():
                            # We need this logic here to avoid the column names
                            # inside the index name
                            index_create = index_create.replace(
                                f"({column_name}", f"(`{column_name}`"
                            )
                            index_create = index_create.replace(
                                f"{column_name},", f"`{column_name}`,"
                            )
                            index_create = index_create.replace(
                                f"{column_name})", f"`{column_name}`)"
                            )

                        index_create = index_create.replace('"', "") + ";"
                        index_create_statements.append(index_create)

                # Add the unique constraints to the create table statement
                if unique_constraints:
                    # Remove the closing parenthesis, semicolon and any
                    # whitespaces at the end of the create table statement
                    create_table_stmt = re.sub(
                        r"\s*\)\s*;\s*$", "", create_table_stmt
                    )
                    create_table_stmt = (
                        create_table_stmt
                        + ", \n\t"
                        + ", \n\t".join(unique_constraints)
                        + "\n);"
                    )

                # Detect self-referential foreign keys from the table schema
                has_self_referential_foreign_keys = False
                for fk in table.foreign_keys:
                    # Check if the foreign key points to the same table
                    if fk.column.table == table:
                        has_self_referential_foreign_keys = True
                        break

                # Store the table schema
                self.store_database_data(
                    dict(
                        table=table.name,
                        create_stmt=create_table_stmt,
                        self_references=has_self_referential_foreign_keys,
                    ),
                    **store_db_kwargs,
                )

                for stmt in index_create_statements:
                    self.store_database_data(
                        dict(
                            table=table.name,
                            index_create_stmt=stmt,
                        ),
                        **store_db_kwargs,
                    )

                # 2. extract the table data in batches
                order_by = [col for col in table.primary_key]

                # Fetch the number of rows in the table
                row_count = conn.scalar(
                    select(func.count()).select_from(table)
                )

                # Fetch the data from the table in batches
                if row_count is not None:
                    batch_size = 100
                    for i in range(0, row_count, batch_size):
                        rows = conn.execute(
                            table.select()
                            .order_by(*order_by)
                            .limit(batch_size)
                            .offset(i)
                        ).fetchall()

                        self.store_database_data(
                            dict(
                                table=table.name,
                                data=[row._asdict() for row in rows],
                            ),
                            **store_db_kwargs,
                        )

    def restore_database_from_storage(
        self,
        **load_db_kwargs: Any,
    ) -> None:
        """Restore the database from a backup storage location.

        Restores the database from an abstract storage location. The storage
        location is implemented by the `load_database_data` method that is
        called repeatedly to load the database information from the external
        storage chunk by chunk.

        Args:
            load_db_kwargs: Additional keyword arguments to pass to the
                `load_database_data` method.
        """
        # Drop and re-create the primary database
        self.create_database(drop=True)

        metadata = MetaData()

        with self.engine.begin() as connection:
            # read the DB information one JSON object at a time
            self_references: dict[str, bool] = {}
            for table_dump in self.load_database_data(**load_db_kwargs):
                table_name = table_dump["table"]
                if "create_stmt" in table_dump:
                    # execute the table creation statement
                    connection.execute(text(table_dump["create_stmt"]))
                    # Reload the database metadata after creating the table
                    metadata.reflect(bind=self.engine)
                    self_references[table_name] = table_dump.get(
                        "self_references", False
                    )

                if "index_create_stmt" in table_dump:
                    # execute the index creation statement
                    connection.execute(text(table_dump["index_create_stmt"]))
                    # Reload the database metadata after creating the index
                    metadata.reflect(bind=self.engine)

                if "data" in table_dump:
                    # insert the data into the database
                    table = metadata.tables[table_name]
                    if self_references.get(table_name, False):
                        # If the table has self-referential foreign keys, we
                        # need to disable the foreign key checks before inserting
                        # the rows and re-enable them afterwards. This is because
                        # the rows need to be inserted in the correct order to
                        # satisfy the foreign key constraints and we don't sort
                        # the rows by creation time in the backup.
                        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

                    for row in table_dump["data"]:
                        # Convert column values to the correct type
                        for column in table.columns:
                            # Blob columns are stored as binary strings
                            if column.type.python_type is bytes and isinstance(
                                row[column.name], str
                            ):
                                # Convert the string to bytes
                                row[column.name] = bytes(
                                    row[column.name], "utf-8"
                                )

                    # Insert the rows into the table in batches
                    batch_size = 100
                    for i in range(0, len(table_dump["data"]), batch_size):
                        connection.execute(
                            table.insert().values(
                                table_dump["data"][i : i + batch_size]
                            )
                        )

                    if table_dump.get("self_references", False):
                        # Re-enable the foreign key checks after inserting the rows
                        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    @abstractmethod
    def store_database_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """Store the database data.

        This method is called repeatedly to store the database information. It
        is called with a single argument, which is a dictionary containing
        either the table schema or table data. The dictionary contains the
        following keys:

            * `table`: The name of the table.
            * `create_stmt`: The table creation statement.
            * `data`: A list of rows in the table.

        The format of the dump is as depicted in the following example:

        ```json
        {
            "table": "table1",
            "create_stmt": "CREATE TABLE table1 (id INTEGER NOT NULL, "
                "name VARCHAR(255), PRIMARY KEY (id))"
        }
        {
            "table": "table1",
            "data": [
            {
                "id": 1,
                "name": "foo"
            },
            {
                "id": 1,
                "name": "bar"
            },
            ...
            ]
        }
        {
            "table": "table1",
            "data": [
            {
                "id": 101,
                "name": "fee"
            },
            {
                "id": 102,
                "name": "bee"
            },
            ...
            ]
        }
        ```

        Args:
            data: The database data to store.
            kwargs: Additional keyword arguments passed to the method.
        """

    @abstractmethod
    def load_database_data(
        self, **kwargs: Any
    ) -> Generator[dict[str, Any], None, None]:
        """Generator that loads the database data.

        This method is called repeatedly to load the database data. It must
        yield a dictionary containing either the table schema or table data,
        as documented in the `store_database_data` method.

        Yields:
            The loaded database data.

        Args:
            kwargs: Additional keyword arguments passed to the method.
        """


class InMemoryDatabaseBackupEngine(SQLAlchemyDatabaseBackupEngine):
    """In-memory database backup engine."""

    def __init__(
        self,
        config: "SqlZenStoreConfiguration",
        location: str | None = None,
    ) -> None:
        """Initialize the in-memory database backup engine.

        Args:
            config: The configuration of the store.
            location: The custom location to store the backup.
        """
        super().__init__(config, location or "memory")
        self.database_data: list[dict[str, Any]] = []
        self._backup_completed: bool = False

    def is_valid_backup(self) -> bool:
        """Check if a valid, completed backup exists.

        Returns:
            Whether a valid completed backup exists.
        """
        return len(self.database_data) > 0 and self._backup_completed

    def store_database_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """Store the database data.

        Args:
            data: The database data to store.
            kwargs: Additional keyword arguments passed to the method.
        """
        self.database_data.append(data)

    def load_database_data(
        self, **kwargs: Any
    ) -> Generator[dict[str, Any], None, None]:
        """Generator that loads the database data.

        Yields:
            The loaded database data.

        Args:
            kwargs: Additional keyword arguments passed to the method.
        """
        for data in self.database_data:
            yield data

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.
        """
        if self.is_valid_backup():
            if not overwrite:
                logger.warning(
                    "An existing backup already exists. Reusing the existing backup."
                )
                return

            self.cleanup_database_backup()
        elif len(self.database_data) > 0:
            self.cleanup_database_backup()

        self._backup_completed = False
        try:
            self.backup_database_to_storage()
            self._backup_completed = True
        except Exception:
            self.cleanup_database_backup()
            raise

        logger.debug("Database backed up to memory.")

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            RuntimeError: If no in-memory backup exists.
        """
        if not self.is_valid_backup():
            raise RuntimeError(
                "No in-memory backup exists. Please backup the database first."
            )

        self.restore_database_from_storage()

        logger.debug("Database restored from memory.")

        if cleanup:
            self.cleanup_database_backup()

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""
        self.database_data = []
        self._backup_completed = False

        logger.debug("In-memory database backup cleaned up.")


class FileDatabaseBackupEngine(SQLAlchemyDatabaseBackupEngine):
    """Database backup engine that stores the database data in a file."""

    def __init__(
        self,
        config: "SqlZenStoreConfiguration",
        location: str | None = None,
    ) -> None:
        """Initialize the file database backup engine.

        Args:
            config: The configuration of the store.
            location: The custom location to store the backup.
        """
        super().__init__(config, location)
        if self._backup_location is None:
            self._backup_location = self._get_db_backup_file_path()

    def _get_db_backup_file_path(self) -> str:
        """Get the path to the database backup.

        Returns:
            The path to the configured database backup.
        """
        from zenml.zen_stores.sql_zen_store import SQLDatabaseDriver

        assert self.url.database is not None

        if self.config.driver == SQLDatabaseDriver.SQLITE:
            return os.path.join(
                self.config.backup_directory,
                # Add the -backup suffix to the database filename
                self.url.database[:-3] + "-backup.db",
            )

        return os.path.join(
            self.config.backup_directory,
            f"{self.url.database}-backup.json",
        )

    def _get_completion_marker_path(self) -> str:
        """Get the path to the backup completion marker file.

        Returns:
            The path to the completion marker file.
        """
        return f"{self.backup_location}.complete"

    def is_valid_backup(self) -> bool:
        """Check if a valid, completed backup exists.

        Returns:
            Whether a valid completed backup exists.
        """
        if not os.path.isfile(self.backup_location):
            return False

        marker_path = self._get_completion_marker_path()
        if not os.path.isfile(marker_path):
            return False

        try:
            with open(marker_path, "r", encoding="utf-8") as f:
                marker_data = json.load(f)
            return marker_data.get("status") == "completed"
        except Exception:
            return False

    def store_database_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """Store the database data.

        Args:
            data: The database data to store.
            **kwargs: Must include `dump_file` (TextIO) - the file handle
                to store the database data.
        """
        dump_file: TextIO = kwargs["dump_file"]
        # Write the data to the JSON file. Use an encoder that
        # can handle datetime, Decimal and other types.
        json.dump(
            data,
            dump_file,
            indent=4,
            default=pydantic_encoder,
        )
        dump_file.write("\n")

    def load_database_data(
        self, **kwargs: Any
    ) -> Generator[dict[str, Any], None, None]:
        """Generator that loads the database data.

        Args:
            **kwargs: Must include `dump_file` (TextIO) - the file handle
                to load the database data from.

        Yields:
            The loaded database data.
        """
        dump_file: TextIO = kwargs["dump_file"]
        buffer = ""
        while True:
            chunk = dump_file.readline()
            if not chunk:
                break
            buffer += chunk
            if chunk.rstrip() == "}":
                yield json.loads(buffer)
                buffer = ""

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.
        """
        if os.path.exists(self.backup_location):
            if not self.is_valid_backup():
                logger.warning(
                    f"An incomplete or invalid backup file was found at "
                    f"`{self.backup_location}`. Cleaning it up before "
                    "creating a fresh backup."
                )
                self.cleanup_database_backup()
            elif not overwrite:
                logger.warning(
                    f"A previous backup file already exists at `{self.backup_location}`. "
                    "Reusing the existing backup."
                )
                return
            else:
                self.cleanup_database_backup()

        backup_dir = os.path.dirname(os.path.abspath(self.backup_location))
        os.makedirs(backup_dir, exist_ok=True)

        unique_id = uuid.uuid4().hex
        staging_file = f"{self.backup_location}.tmp.{unique_id}"
        marker_path = self._get_completion_marker_path()
        staging_marker = f"{marker_path}.tmp.{unique_id}"

        try:
            if self.url.drivername == "sqlite":
                # For a sqlite database, copy to the staging file
                assert self.url.database is not None
                shutil.copyfile(
                    self.url.database,
                    staging_file,
                )
            else:
                with open(staging_file, "w", encoding="utf-8") as f:
                    self.backup_database_to_storage(dump_file=f)

            # Write the completion marker to staging
            marker_data = {
                "status": "completed",
                "backup_location": self.backup_location,
                "timestamp": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
            }
            with open(staging_marker, "w", encoding="utf-8") as f:
                json.dump(marker_data, f)

            # Promote staging files atomically to their final locations
            os.replace(staging_file, self.backup_location)
            os.replace(staging_marker, marker_path)
        except Exception:
            if os.path.isfile(staging_file):
                try:
                    os.remove(staging_file)
                except OSError:
                    pass
            if os.path.isfile(staging_marker):
                try:
                    os.remove(staging_marker)
                except OSError:
                    pass
            raise

        logger.debug(f"Database backed up to file `{self.backup_location}`.")

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            RuntimeError: If the backup file does not exist or is not accessible.
        """
        if not self.is_valid_backup():
            raise RuntimeError(
                f"Database backup file `{self.backup_location}` does not "
                "exist, is incomplete, or is not accessible."
            )

        if self.url.drivername == "sqlite":
            # For a sqlite database, we just overwrite the database file
            # with the backup file
            assert self.url.database is not None
            shutil.copyfile(
                self.backup_location,
                self.url.database,
            )
            return

        with open(self.backup_location, "r", encoding="utf-8") as f:
            self.restore_database_from_storage(dump_file=f)

        logger.debug(f"Database restored from file `{self.backup_location}`.")

        if cleanup:
            self.cleanup_database_backup()

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""
        if os.path.isfile(self.backup_location):
            try:
                os.remove(self.backup_location)
            except OSError:
                logger.warning(
                    f"Failed to cleanup database dump file `{self.backup_location}`."
                )
            else:
                logger.info(
                    f"Successfully cleaned up database dump file "
                    f"`{self.backup_location}`."
                )

        marker_path = self._get_completion_marker_path()
        if os.path.isfile(marker_path):
            try:
                os.remove(marker_path)
            except OSError:
                logger.warning(
                    f"Failed to cleanup backup completion marker `{marker_path}`."
                )
            else:
                logger.info(
                    f"Successfully cleaned up backup completion marker `{marker_path}`."
                )

        # Cleanup any lingering temporary staging files
        backup_dir = os.path.dirname(os.path.abspath(self.backup_location))
        if os.path.isdir(backup_dir):
            base_name = os.path.basename(self.backup_location)
            try:
                for fname in os.listdir(backup_dir):
                    if fname.startswith(
                        f"{base_name}.tmp."
                    ) or fname.startswith(
                        f"{os.path.basename(marker_path)}.tmp."
                    ):
                        try:
                            os.remove(os.path.join(backup_dir, fname))
                        except OSError:
                            pass
            except OSError:
                pass


class DBCloneDatabaseBackupEngine(BaseDatabaseBackupEngine):
    """Database backup engine that copies the database to a new database."""

    def __init__(
        self,
        config: "SqlZenStoreConfiguration",
        location: str | None = None,
    ) -> None:
        """Initialize the database backup engine.

        Args:
            config: The configuration of the store.
            location: The custom location to store the backup.

        Raises:
            ValueError: If the backup database name is not set in the store
                configuration.
        """
        super().__init__(config, location)
        if self._backup_location is None:
            if self.config.backup_database is None:
                raise ValueError(
                    "The backup database name must be set in the store "
                    "configuration to use the backup database strategy."
                )
            self._backup_location = self.config.backup_database

    @classmethod
    def _copy_database(cls, src_engine: Engine, dst_engine: Engine) -> None:
        """Copy the database from one engine to another.

        This method assumes that the destination database exists and is empty.

        Args:
            src_engine: The source SQLAlchemy engine.
            dst_engine: The destination SQLAlchemy engine.
        """
        src_metadata = MetaData()
        src_metadata.reflect(bind=src_engine)

        dst_metadata = MetaData()
        dst_metadata.reflect(bind=dst_engine)

        # @event.listens_for(src_metadata, "column_reflect")
        # def generalize_datatypes(inspector, tablename, column_dict):
        #     column_dict["type"] = column_dict["type"].as_generic(allow_nulltype=True)

        # Create all tables in the target database
        for table in src_metadata.sorted_tables:
            if table.name == "_zenml_backup_metadata":
                continue
            table.create(bind=dst_engine)

        # Refresh target metadata after creating the tables
        dst_metadata.clear()
        dst_metadata.reflect(bind=dst_engine)

        # Copy all data from the source database to the destination database
        with src_engine.begin() as src_conn:
            with dst_engine.begin() as dst_conn:
                for src_table in src_metadata.sorted_tables:
                    if src_table.name == "_zenml_backup_metadata":
                        continue
                    dst_table = dst_metadata.tables[src_table.name]
                    insert = dst_table.insert()

                    # If the table has a `created` column, we use it to sort
                    # the rows in the table starting with the oldest rows.
                    # This is to ensure that the rows are inserted in the
                    # correct order, since some tables have inner foreign key
                    # constraints.
                    if "created" in src_table.columns:
                        order_by = [src_table.columns["created"]]
                    else:
                        order_by = []
                    if "id" in src_table.columns:
                        # If the table has an `id` column, we also use it to
                        # sort the rows in the table, even if we already use
                        # "created" to sort the rows. We need a unique field to
                        # sort the rows, to break the tie between rows with the
                        # same "created" date, otherwise the same entry might
                        # end up multiple times in subsequent pages.
                        order_by.append(src_table.columns["id"])

                    row_count = src_conn.scalar(
                        select(func.count()).select_from(src_table)
                    )

                    # Copy rows in batches
                    if row_count is not None:
                        batch_size = 50
                        for i in range(0, row_count, batch_size):
                            rows = src_conn.execute(
                                src_table.select()
                                .order_by(*order_by)
                                .limit(batch_size)
                                .offset(i)
                            ).fetchall()

                            dst_conn.execute(
                                insert, [row._asdict() for row in rows]
                            )

    def is_valid_backup(self) -> bool:
        """Check if a valid, completed backup exists.

        Returns:
            Whether a valid completed backup exists.
        """
        if not self.database_exists(database=self.backup_location):
            return False

        try:
            backup_engine = self.create_engine(database=self.backup_location)
            with backup_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT status FROM `_zenml_backup_metadata` LIMIT 1")
                ).scalar()
                return result == "completed"
        except Exception:
            return False

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.
        """
        if self.database_exists(database=self.backup_location):
            if not self.is_valid_backup():
                logger.warning(
                    f"An incomplete backup database already exists at "
                    f"`{self.backup_location}`. Cleaning it up before "
                    "creating a fresh backup."
                )
                self.cleanup_database_backup()
            elif not overwrite:
                logger.warning(
                    f"A previous backup database already exists at "
                    f"`{self.backup_location}`. Reusing the existing backup."
                )
                return
            else:
                self.cleanup_database_backup()

        self.create_database(
            database=self.backup_location,
            drop=True,
        )

        backup_engine = self.create_engine(database=self.backup_location)

        try:
            self._copy_database(self.engine, backup_engine)
            with backup_engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS `_zenml_backup_metadata` "
                        "(`status` VARCHAR(32) PRIMARY KEY)"
                    )
                )
                conn.execute(
                    text(
                        "INSERT INTO `_zenml_backup_metadata` (`status`) "
                        "VALUES ('completed')"
                    )
                )
        except Exception:
            self.cleanup_database_backup()
            raise

        logger.debug(
            f"Database backed up to the `{self.backup_location}` backup database."
        )

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            RuntimeError: If the backup database does not exist.
        """
        if not self.is_valid_backup():
            raise RuntimeError(
                f"Backup database `{self.backup_location}` does not exist "
                "or is incomplete."
            )

        backup_engine = self.create_engine(database=self.backup_location)

        self.create_database(drop=True)

        self._copy_database(backup_engine, self.engine)

        logger.debug(
            f"Database restored from the `{self.backup_location}` backup database."
        )

        if cleanup:
            self.cleanup_database_backup()

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""
        if self.database_exists(database=self.backup_location):
            self.drop_database(
                database=self.backup_location,
            )
            logger.debug(
                f"Successfully cleaned up backup database "
                f"{self.backup_location}."
            )
