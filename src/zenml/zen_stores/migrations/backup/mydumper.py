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
from typing import TYPE_CHECKING

from zenml.enums import LoggingLevels
from zenml.logger import get_logger, get_logging_level
from zenml.zen_stores.migrations.backup.base import BaseDatabaseBackupEngine

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

# Mapping from Python logging levels to mydumper/myloader verbosity:
# mydumper: 0 = silent, 1 = errors, 2 = warnings, 3 = info
LOGGING_LEVEL_TO_MYDUMPER_VERBOSITY = {
    LoggingLevels.NOTSET: 0,
    LoggingLevels.DEBUG: 3,
    LoggingLevels.INFO: 2,
    LoggingLevels.WARNING: 2,
    LoggingLevels.WARN: 2,
    LoggingLevels.ERROR: 1,
    LoggingLevels.CRITICAL: 1,
}


class MyDumperDatabaseBackupEngine(BaseDatabaseBackupEngine):
    """Database backup engine that uses mydumper/myloader for parallel backup/restore."""

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
        self._check_mydumper_installed()
        self._check_myloader_installed()

        super().__init__(config, location)
        if self._backup_location is None:
            self._backup_location = os.path.join(
                self.config.backup_directory,
                f"{self.url.database}-backup",
            )

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

    def _get_mysql_connection_args(self) -> list[str]:
        """Build MySQL connection arguments for mydumper/myloader.

        Returns:
            List of command-line arguments for MySQL connection.
        """
        args: list[str] = []

        if self.url.host:
            args.extend(["--host", self.url.host])

        if self.url.port:
            args.extend(["--port", str(self.url.port)])

        if self.url.username:
            args.extend(["--user", self.url.username])

        if self.config.ssl:
            args.extend(["--ssl", "--ssl-mode", "REQUIRED"])
            if self.config.ssl_ca:
                args.extend(["--ca", self.config.ssl_ca.get_secret_value()])
            if self.config.ssl_cert:
                args.extend(
                    ["--cert", self.config.ssl_cert.get_secret_value()]
                )
            if self.config.ssl_key:
                args.extend(["--key", self.config.ssl_key.get_secret_value()])

        return args

    def _get_mysql_env(self) -> dict[str, str] | None:
        """Build environment variables for MySQL authentication.

        Returns:
            Dictionary of environment variables to pass to subprocess,
            or None if no password is configured.
        """
        if self.url.password:
            return {"MYSQL_PWD": self.url.password}

        return None

    @staticmethod
    def _get_mydumper_verbosity() -> int:
        """Map ZenML's logging level to mydumper/myloader verbosity.

        Returns:
            The mydumper verbosity level (0-3).
        """
        current_level = get_logging_level()
        return LOGGING_LEVEL_TO_MYDUMPER_VERBOSITY.get(current_level, 2)

    def _build_mydumper_command(self) -> list[str]:
        """Build the mydumper command for database backup.

        Returns:
            List of command-line arguments for mydumper.
        """
        assert self.url.database is not None
        cmd = ["mydumper"]
        cmd.extend(self._get_mysql_connection_args())
        cmd.extend(["--database", self.url.database])
        cmd.extend(["--outputdir", self.backup_location])
        cmd.extend(["--verbose", str(self._get_mydumper_verbosity())])

        if self.config.mydumper_threads:
            cmd.extend(["--threads", str(self.config.mydumper_threads)])

        if self.config.mydumper_compress:
            cmd.append("--compress")

        if self.config.mydumper_extra_args:
            cmd.extend(self.config.mydumper_extra_args)

        return cmd

    def _build_myloader_command(self) -> list[str]:
        """Build the myloader command for database restore.

        Returns:
            List of command-line arguments for myloader.
        """
        assert self.url.database is not None
        cmd = ["myloader"]
        cmd.extend(self._get_mysql_connection_args())
        cmd.extend(["--database", self.url.database])
        cmd.extend(["--directory", self.backup_location])
        cmd.extend(["--verbose", str(self._get_mydumper_verbosity())])
        cmd.append("--overwrite-tables")

        if self.config.myloader_threads:
            cmd.extend(["--threads", str(self.config.myloader_threads)])

        if self.config.myloader_extra_args:
            cmd.extend(self.config.myloader_extra_args)

        return cmd

    def backup_database(
        self,
        overwrite: bool = False,
    ) -> None:
        """Backup the database.

        Args:
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.

        Raises:
            RuntimeError: If the backup process fails.
        """
        if os.path.isdir(self.backup_location):
            if not overwrite:
                logger.warning(
                    f"Backup directory `{self.backup_location}` already exists. "
                    "Reusing the existing backup."
                )
                return

            self.cleanup_database_backup()

        os.makedirs(self.backup_location, exist_ok=True)

        cmd = self._build_mydumper_command()

        logger.info(
            f"Starting mydumper backup of database `{self.url.database}` "
            f"to `{self.backup_location}`"
        )
        logger.debug(f"mydumper command: {cmd}")

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
            f"Database `{self.url.database}` successfully backed up "
            f"to `{self.backup_location}`"
        )

    def restore_database(
        self,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            RuntimeError: If the backup directory does not exist or if the
                restore process fails.
        """
        if not os.path.isdir(self.backup_location):
            raise RuntimeError(
                f"Backup directory `{self.backup_location}` does not exist. "
                "Please backup the database first."
            )

        # Drop and re-create the primary database
        self.create_database(drop=True)

        cmd = self._build_myloader_command()

        logger.info(
            f"Starting myloader restore of database `{self.url.database}` "
            f"from `{self.backup_location}`"
        )
        logger.debug(f"myloader command: {cmd}")

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
            f"Database `{self.url.database}` successfully restored "
            f"from `{self.backup_location}`"
        )

        if cleanup:
            self.cleanup_database_backup()

    def cleanup_database_backup(
        self,
    ) -> None:
        """Delete the database backup."""
        if os.path.isdir(self.backup_location):
            shutil.rmtree(self.backup_location)
            logger.info(
                f"Successfully cleaned up database backup `{self.backup_location}`."
            )
