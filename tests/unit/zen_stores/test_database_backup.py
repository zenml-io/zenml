# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
"""Tests for database backup engines and atomic writes."""

import json
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest

from zenml.zen_stores.migrations.backup.base import (
    BaseDatabaseBackupEngine,
    DisabledDatabaseBackupEngine,
)
from zenml.zen_stores.migrations.backup.mydumper import (
    MyDumperDatabaseBackupEngine,
)
from zenml.zen_stores.migrations.backup.sqlalchemy import (
    DBCloneDatabaseBackupEngine,
    FileDatabaseBackupEngine,
    InMemoryDatabaseBackupEngine,
)


@pytest.fixture
def dummy_store_config(tmp_path):
    """Create a dummy SqlZenStoreConfiguration."""
    config = MagicMock()
    config.backup_directory = str(tmp_path / "backups")
    os.makedirs(config.backup_directory, exist_ok=True)
    url = MagicMock()
    url.drivername = "sqlite"
    url.database = str(tmp_path / "zenml.db")
    url._replace.return_value = url
    config.get_sqlalchemy_config.return_value = (url, {}, {})
    config.configure_engine_auth = MagicMock()
    return config


def test_file_backup_engine_atomic_write_and_completion_marker(
    tmp_path, dummy_store_config
):
    """Test that file backup creates the final file and completion marker atomically."""
    # Create the source database file
    db_file = tmp_path / "zenml.db"
    db_file.write_text("dummy database content")

    engine = FileDatabaseBackupEngine(config=dummy_store_config)
    assert not engine.is_valid_backup()

    engine.backup_database(overwrite=False)

    assert os.path.isfile(engine.backup_location)
    marker_path = engine._get_completion_marker_path()
    assert os.path.isfile(marker_path)
    with open(marker_path, "r", encoding="utf-8") as f:
        marker = json.load(f)
    assert marker["status"] == "completed"
    assert engine.is_valid_backup()

    # Cleanup removes both
    engine.cleanup_database_backup()
    assert not os.path.isfile(engine.backup_location)
    assert not os.path.isfile(marker_path)
    assert not engine.is_valid_backup()


def test_file_backup_engine_failure_cleans_up_staging(
    tmp_path, dummy_store_config
):
    """Test that a failed backup cleans up staging and does not leave a partial backup."""
    db_file = tmp_path / "zenml.db"
    db_file.write_text("dummy database content")

    engine = FileDatabaseBackupEngine(config=dummy_store_config)

    with patch(
        "shutil.copyfile", side_effect=IOError("Simulated disk write failure")
    ):
        with pytest.raises(IOError):
            engine.backup_database(overwrite=False)

    # Destination and marker should not exist
    assert not os.path.exists(engine.backup_location)
    assert not os.path.exists(engine._get_completion_marker_path())
    assert not engine.is_valid_backup()

    # Staging files should have been cleaned up
    backup_dir = dummy_store_config.backup_directory
    staging_files = [f for f in os.listdir(backup_dir) if ".tmp." in f]
    assert len(staging_files) == 0


def test_file_backup_engine_replaces_incomplete_backup_when_overwrite_false(
    tmp_path, dummy_store_config
):
    """Test that an incomplete existing backup artifact is detected, cleaned up, and replaced."""
    db_file = tmp_path / "zenml.db"
    db_file.write_text("complete database content")

    engine = FileDatabaseBackupEngine(config=dummy_store_config)

    # Simulate an incomplete/corrupted backup file left from a previous interrupted run
    with open(engine.backup_location, "w", encoding="utf-8") as f:
        f.write("partial truncated content")

    # Without completion marker, it is not a valid backup
    assert os.path.isfile(engine.backup_location)
    assert not engine.is_valid_backup()

    # Running backup with overwrite=False should NOT reuse the corrupt file
    engine.backup_database(overwrite=False)

    assert engine.is_valid_backup()
    with open(engine.backup_location, "r", encoding="utf-8") as f:
        assert f.read() == "complete database content"


def test_file_backup_engine_restore_refuses_incomplete_backup(
    tmp_path, dummy_store_config
):
    """Test that restore_database raises an error if the backup is incomplete."""
    engine = FileDatabaseBackupEngine(config=dummy_store_config)

    # Write a partial file without marker
    with open(engine.backup_location, "w", encoding="utf-8") as f:
        f.write("partial content")

    assert not engine.is_valid_backup()

    with pytest.raises(RuntimeError, match="incomplete|does not exist"):
        engine.restore_database()


def test_in_memory_backup_engine_failure_resets_state(dummy_store_config):
    """Test that InMemoryDatabaseBackupEngine cleans up on failure."""
    engine = InMemoryDatabaseBackupEngine(config=dummy_store_config)
    assert not engine.is_valid_backup()

    with patch.object(
        engine,
        "backup_database_to_storage",
        side_effect=RuntimeError("Storage failure"),
    ):
        with pytest.raises(RuntimeError):
            engine.backup_database(overwrite=False)

    assert not engine.is_valid_backup()
    assert len(engine.database_data) == 0

    with pytest.raises(RuntimeError):
        engine.restore_database()


def test_mydumper_backup_engine_failure_cleans_up_staging(dummy_store_config):
    """Test that a failed mydumper backup cleans up staging and leaves no target directory."""
    with (
        patch.object(
            MyDumperDatabaseBackupEngine, "_check_mydumper_installed"
        ),
        patch.object(
            MyDumperDatabaseBackupEngine, "_check_myloader_installed"
        ),
    ):
        engine = MyDumperDatabaseBackupEngine(config=dummy_store_config)

    mock_process = MagicMock()
    mock_process.stdout = ["error occurred"]
    mock_process.wait.return_value = 1

    with patch("subprocess.Popen", return_value=mock_process):
        with pytest.raises(RuntimeError, match="failed with return code 1"):
            engine.backup_database(overwrite=False)

    assert not os.path.exists(engine.backup_location)
    assert not engine.is_valid_backup()

    # Ensure no leftover staging directory
    parent_dir = dummy_store_config.backup_directory
    staging_dirs = [d for d in os.listdir(parent_dir) if ".tmp." in d]
    assert len(staging_dirs) == 0


def test_mydumper_backup_engine_replaces_incomplete_directory(
    tmp_path, dummy_store_config
):
    """Test that an incomplete directory from interrupted mydumper is rejected and replaced."""
    with (
        patch.object(
            MyDumperDatabaseBackupEngine, "_check_mydumper_installed"
        ),
        patch.object(
            MyDumperDatabaseBackupEngine, "_check_myloader_installed"
        ),
    ):
        engine = MyDumperDatabaseBackupEngine(config=dummy_store_config)

    # Create incomplete directory without completion marker
    os.makedirs(engine.backup_location, exist_ok=True)
    with open(os.path.join(engine.backup_location, "partial.sql"), "w") as f:
        f.write("partial sql")

    assert not engine.is_valid_backup()

    # Restore must refuse to run
    with pytest.raises(RuntimeError, match="incomplete|does not exist"):
        engine.restore_database()

    # Backup with successful process should replace it
    mock_process = MagicMock()
    mock_process.stdout = ["backup succeeded"]
    mock_process.wait.return_value = 0

    with patch("subprocess.Popen", return_value=mock_process):
        engine.backup_database(overwrite=False)

    assert engine.is_valid_backup()
    marker_file = engine._get_completion_marker_path()
    assert os.path.isfile(marker_file)


def test_backup_database_context_raises_if_verification_fails(
    dummy_store_config,
):
    """Test that backup_database_context aborts if verification fails."""
    engine = InMemoryDatabaseBackupEngine(config=dummy_store_config)

    with (
        patch.object(engine, "backup_database"),
        patch.object(engine, "is_valid_backup", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="verification failed"):
            with engine.backup_database_context():
                pass
