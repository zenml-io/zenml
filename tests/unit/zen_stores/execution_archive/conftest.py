#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Fixtures shared by the execution archive tests."""

import json
from pathlib import Path
from typing import Iterator

import pytest

from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def bare_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """A fresh SQLite-backed store without archive storage configured."""
    config_dir = tmp_path / "zenml-config"
    config_dir.mkdir()
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(config_dir))
    monkeypatch.delenv("ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR", raising=False)
    monkeypatch.delenv(
        "ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION", raising=False
    )
    yield SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{config_dir / 'zenml.db'}"
        ),
        skip_default_registrations=False,
    )


@pytest.fixture
def sql_store(
    bare_store: SqlZenStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> SqlZenStore:
    """A store with a local archive storage configured on the server."""
    monkeypatch.setenv("ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR", "local")
    monkeypatch.setenv(
        "ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION",
        json.dumps({"path": str(tmp_path / "archive-primary")}),
    )
    return bare_store
