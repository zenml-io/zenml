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
"""ZenML database migration, backup and recovery utilities."""

import json
import os
import re
import shutil
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    cast,
)

import pymysql
from pydantic import BaseModel, ConfigDict
from sqlalchemy import MetaData, func, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import (
    OperationalError,
)
from sqlalchemy.schema import CreateTable
from sqlmodel import (
    create_engine,
    select,
)

from zenml.logger import get_logger
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)


class MigrationUtils(BaseModel):
    """Utilities for database migration, backup and recovery."""

    url: URL
    connect_args: Dict[str, Any]
    engine_args: Dict[str, Any]

    _engine: Optional[Engine] = None
    _master_engine: Optional[Engine] = None

    def create_engine(self, database: Optional[str] = None) -> Engine:
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
        database: Optional[str] = None,
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
        database: Optional[str] = None,
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
        database: Optional[str] = None,
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

    def backup_database_to_storage(
        self, store_db_info: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Backup the database to a storage location.

        Backup the database to an abstract storage location. The storage
        location is specified by a function that is called repeatedly to
        store the database information. The function is called with a single
        argument, which is a dictionary containing either the table schema or
        table data. The dictionary contains the following keys:

            * `table`: The name of the table.
            * `create_stmt`: The table creation statement.
            * `data`: A list of rows in the table.

        Args:
            store_db_info: The function to call to store the database
                information.
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
                unique_constraints = []
                for index in table.indexes:
                    if index.unique:
                        unique_columns = [
                            f"`{column.name}`" for column in index.columns
                        ]
                        unique_constraints.append(
                            f"UNIQUE KEY `{index.name}` ({', '.join(unique_columns)})"
                        )

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
                store_db_info(
                    dict(
                        table=table.name,
                        create_stmt=create_table_stmt,
                        self_references=has_self_referential_foreign_keys,
                    )
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

                        store_db_info(
                            dict(
                                table=table.name,
                                data=[row._asdict() for row in rows],
                            ),
                        )

    def restore_database_from_storage(
        self, load_db_info: Callable[[], Generator[Dict[str, Any], None, None]]
    ) -> None:
        """Restore the database from a backup storage location.

        Restores the database from an abstract storage location. The storage
        location is specified by a function that is called repeatedly to
        load the database information from the external storage chunk by chunk.
        The function must yield a dictionary containing either the table schema
        or table data. The dictionary contains the following keys:

            * `table`: The name of the table.
            * `create_stmt`: The table creation statement.
            * `data`: A list of rows in the table.

        The function must return `None` when there is no more data to load.

        Args:
            load_db_info: The function to call to load the database
                information.
        """
        # Drop and re-create the primary database
        self.create_database(drop=True)

        metadata = MetaData()

        with self.engine.begin() as connection:
            # read the DB information one JSON object at a time
            self_references: Dict[str, bool] = {}
            for table_dump in load_db_info():
                table_name = table_dump["table"]
                if "create_stmt" in table_dump:
                    # execute the table creation statement
                    connection.execute(text(table_dump["create_stmt"]))
                    # Reload the database metadata after creating the table
                    metadata.reflect(bind=self.engine)
                    self_references[table_name] = table_dump.get(
                        "self_references", False
                    )

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

    def backup_database_to_file(self, dump_file: str) -> None:
        """Backup the database to a file.

        This method dumps the entire database into a JSON file. Instead of
        using a SQL dump, we use a proprietary JSON dump because:

            * it is (mostly) not dependent on the SQL dialect or database version
            * it is safer with respect to SQL injection attacks
            * it is easier to read and debug

        The JSON file contains a list of JSON objects instead of a single JSON
        object, because it allows for buffered reading and writing of the file
        and thus reduces the memory footprint. Each JSON object can contain
        either schema or data information about a single table. For tables with
        a large amount of data, the data is split into multiple JSON objects
        with the first object always containing the schema.

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
            dump_file: The path to the dump file.
        """
        # create the directory if it does not exist
        dump_path = os.path.dirname(os.path.abspath(dump_file))
        if not os.path.exists(dump_path):
            os.makedirs(dump_path)

        if self.url.drivername == "sqlite":
            # For a sqlite database, we can just make a copy of the database
            # file
            assert self.url.database is not None
            shutil.copyfile(
                self.url.database,
                dump_file,
            )
            return

        with open(dump_file, "w") as f:

            def json_dump(obj: Dict[str, Any]) -> None:
                """Dump a JSON object to the dump file.

                Args:
                    obj: The JSON object to dump.
                """
                # Write the data to the JSON file. Use an encoder that
                # can handle datetime, Decimal and other types.
                json.dump(
                    obj,
                    f,
                    indent=4,
                    default=pydantic_encoder,
                )
                f.write("\n")

            # Call the generic backup method with a function that dumps the
            # JSON objects to the dump file
            self.backup_database_to_storage(json_dump)

        logger.debug(f"Database backed up to {dump_file}")

    def restore_database_from_file(self, dump_file: str) -> None:
        """Restore the database from a backup dump file.

        See the documentation of the `backup_database_to_file` method for
        details on the format of the dump file.

        Args:
            dump_file: The path to the dump file.

        Raises:
            RuntimeError: If the database cannot be restored successfully.
        """
        if not os.path.exists(dump_file):
            raise RuntimeError(
                f"Database backup file '{dump_file}' does not "
                f"exist or is not accessible."
            )

        if self.url.drivername == "sqlite":
            # For a sqlite database, we just overwrite the database file
            # with the backup file
            assert self.url.database is not None
            shutil.copyfile(
                dump_file,
                self.url.database,
            )
            return

        # read the DB dump file one JSON object at a time
        with open(dump_file, "r") as f:

            def json_load() -> Generator[Dict[str, Any], None, None]:
                """Generator that loads the JSON objects in the dump file.

                Yields:
                    The loaded JSON objects.
                """
                buffer = ""
                while True:
                    chunk = f.readline()
                    if not chunk:
                        break
                    buffer += chunk
                    if chunk.rstrip() == "}":
                        yield json.loads(buffer)
                        buffer = ""

            # Call the generic restore method with a function that loads the
            # JSON objects from the dump file
            self.restore_database_from_storage(json_load)

        logger.info(f"Database successfully restored from '{dump_file}'")

    def backup_database_to_memory(self) -> List[Dict[str, Any]]:
        """Backup the database in memory.

        Returns:
            The in-memory representation of the database backup.

        Raises:
            RuntimeError: If the database cannot be backed up successfully.
        """
        if self.url.drivername == "sqlite":
            # For a sqlite database, this is not supported.
            raise RuntimeError(
                "In-memory backup is not supported for sqlite databases."
            )

        db_dump: List[Dict[str, Any]] = []

        def store_in_mem(obj: Dict[str, Any]) -> None:
            """Store a JSON object in the in-memory database backup.

            Args:
                obj: The JSON object to store.
            """
            db_dump.append(obj)

        # Call the generic backup method with a function that stores the
        # JSON objects in the in-memory database backup
        self.backup_database_to_storage(store_in_mem)

        logger.debug("Database backed up in memory")

        return db_dump

    def restore_database_from_memory(
        self, db_dump: List[Dict[str, Any]]
    ) -> None:
        """Restore the database from an in-memory backup.

        Args:
            db_dump: The in-memory database backup to restore from generated
                by the `backup_database_to_memory` method.

        Raises:
            RuntimeError: If the database cannot be restored successfully.
        """
        if self.url.drivername == "sqlite":
            # For a sqlite database, this is not supported.
            raise RuntimeError(
                "In-memory backup is not supported for sqlite databases."
            )

        def load_from_mem() -> Generator[Dict[str, Any], None, None]:
            """Generator that loads the JSON objects from the in-memory backup.

            Yields:
                The loaded JSON objects.
            """
            for obj in db_dump:
                yield obj

        # Call the generic restore method with a function that loads the
        # JSON objects from the in-memory database backup
        self.restore_database_from_storage(load_from_mem)

        logger.info("Database successfully restored from memory")

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
            table.create(bind=dst_engine)

        # Refresh target metadata after creating the tables
        dst_metadata.clear()
        dst_metadata.reflect(bind=dst_engine)

        # Copy all data from the source database to the destination database
        with src_engine.begin() as src_conn:
            with dst_engine.begin() as dst_conn:
                for src_table in src_metadata.sorted_tables:
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

    def backup_database_to_db(self, backup_db_name: str) -> None:
        """Backup the database to a backup database.

        Args:
            backup_db_name: Backup database name to backup to.
        """
        # Re-create the backup database
        self.create_database(
            database=backup_db_name,
            drop=True,
        )

        backup_engine = self.create_engine(database=backup_db_name)

        self._copy_database(self.engine, backup_engine)

        logger.debug(
            f"Database backed up to the `{backup_db_name}` backup database."
        )

    def restore_database_from_db(self, backup_db_name: str) -> None:
        """Restore the database from the backup database.

        Args:
            backup_db_name: Backup database name to restore from.

        Raises:
            RuntimeError: If the backup database does not exist.
        """
        if not self.database_exists(database=backup_db_name):
            raise RuntimeError(
                f"Backup database `{backup_db_name}` does not exist."
            )

        backup_engine = self.create_engine(database=backup_db_name)

        # Drop and re-create the primary database
        self.create_database(
            drop=True,
        )

        self._copy_database(backup_engine, self.engine)

        logger.debug(
            f"Database restored from the `{backup_db_name}` "
            "backup database."
        )

    model_config = ConfigDict(arbitrary_types_allowed=True)
