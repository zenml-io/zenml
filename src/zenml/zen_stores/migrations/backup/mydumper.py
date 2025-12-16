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
"""Base class for the mydumper/myloader database backup engine."""

import os
import shutil
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.engine import URL

from zenml.logger import get_logger
from zenml.zen_stores.migrations.backup.base import BaseDatabaseBackupEngine

logger = get_logger(__name__)


class MyDumperDatabaseBackupEngine(BaseDatabaseBackupEngine):
    """Database backup engine that uses mydumper/myloader for parallel backup/restore."""

    def __init__(
        self,
        url: URL,
        connect_args: Dict[str, Any],
        engine_args: Dict[str, Any],
        backup_dir: str,
        threads: int = 4,
        compress: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> None:
        """Initialize the backup engine.

        Args:
            url: The URL of the database to backup.
            connect_args: The connect arguments for the SQLAlchemy engine.
            engine_args: The engine arguments for the SQLAlchemy engine.
            backup_dir: The directory where the backup will be stored.
            threads: The number of threads to use for parallel backup/restore.
            compress: Whether to compress the backup files.
            extra_args: Additional arguments to pass to mydumper/myloader.
        """
        self._check_mydumper_installed()
        self._check_myloader_installed()

        super().__init__(url, connect_args, engine_args)
        self.backup_dir = backup_dir
        self.threads = threads
        self.compress = compress
        self.extra_args = extra_args

    @staticmethod
    def _check_mydumper_installed() -> None:
        """Verify that mydumper is installed and available.

        Raises:
            RuntimeError: If mydumper is not found in the system PATH.
        """
        if shutil.which("mydumper") is None:
            raise RuntimeError(
                "mydumper is not installed or not available in PATH. "
                "Please install mydumper to use this backup method."
            )

    @staticmethod
    def _check_myloader_installed() -> None:
        """Verify that myloader is installed and available.

        Raises:
            RuntimeError: If myloader is not found in the system PATH.
        """
        if shutil.which("myloader") is None:
            raise RuntimeError(
                "myloader is not installed or not available in PATH. "
                "Please install myloader to use this restore method."
            )

    def _get_mysql_connection_args(self) -> List[str]:
        """Build MySQL connection arguments for mydumper/myloader.

        Returns:
            List of command-line arguments for MySQL connection.

        Raises:
            RuntimeError: If required connection parameters are missing.
        """
        args: List[str] = []

        if self.url.host:
            args.extend(["--host", self.url.host])

        if self.url.port:
            args.extend(["--port", str(self.url.port)])

        if self.url.username:
            args.extend(["--user", self.url.username])

        return args

    def _get_mysql_env(self) -> Optional[Dict[str, str]]:
        """Build environment variables for MySQL authentication.

        Returns:
            Dictionary of environment variables to pass to subprocess,
            or None if no password is configured.
        """
        if self.url.password:
            return {"MYSQL_PWD": self.url.password}
        return None

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.

        Raises:
            RuntimeError: If the backup directory already exists, if the
                database name is not set, or if the backup process fails.
        """
        if os.path.isdir(self.backup_dir):
            if not overwrite:
                raise RuntimeError(
                    f"Backup directory '{self.backup_dir}' already exists. "
                    "Reusing the existing backup."
                )
            else:
                self.cleanup_database_backup()

        if not self.url.database:
            raise RuntimeError(
                "Database name is required for mydumper backup."
            )

        os.makedirs(self.backup_dir, exist_ok=True)

        cmd = ["mydumper"]
        cmd.extend(self._get_mysql_connection_args())
        cmd.extend(["--database", self.url.database])
        cmd.extend(["--outputdir", self.backup_dir])
        cmd.extend(["--threads", str(self.threads)])

        if self.compress:
            cmd.append("--compress")

        if self.extra_args:
            cmd.extend(self.extra_args)

        logger.info(
            f"Starting mydumper backup of database '{self.url.database}' "
            f"to '{self.backup_dir}'"
        )

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self._get_mysql_env(),
        )

        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.info(f"[mydumper] {line}")

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"mydumper backup failed with return code {return_code}"
            )

        logger.info(
            f"Database '{self.url.database}' successfully backed up "
            f"to '{self.backup_dir}'"
        )

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            RuntimeError: If the backup directory does not exist, if the
                database name is not set, or if the restore process fails.
        """
        if not os.path.isdir(self.backup_dir):
            raise RuntimeError(
                f"Backup directory '{self.backup_dir}' does not exist. "
                "Please backup the database first."
            )

        if not self.url.database:
            raise RuntimeError(
                "Database name is required for myloader restore."
            )

        # Drop and re-create the primary database
        self.create_database(drop=True)

        cmd = ["myloader"]
        cmd.extend(self._get_mysql_connection_args())
        cmd.extend(["--database", self.url.database])
        cmd.extend(["--directory", self.backup_dir])
        cmd.extend(["--threads", str(self.threads)])
        cmd.append("--overwrite-tables")

        if self.extra_args:
            cmd.extend(self.extra_args)

        logger.info(
            f"Starting myloader restore of database '{self.url.database}' "
            f"from '{self.backup_dir}'"
        )

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self._get_mysql_env(),
        )

        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.info(f"[myloader] {line}")

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"myloader restore failed with return code {return_code}"
            )

        logger.info(
            f"Database '{self.url.database}' successfully restored "
            f"from '{self.backup_dir}'"
        )

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""
        if os.path.isdir(self.backup_dir):
            shutil.rmtree(self.backup_dir)
            logger.info(
                f"Successfully cleaned up database backup '{self.backup_dir}'."
            )

    @property
    def backup_location(self) -> str:
        """The location where the database is backed up to.

        Returns:
            The location where the database is backed up to.
        """
        return f"`{self.backup_dir}`"
