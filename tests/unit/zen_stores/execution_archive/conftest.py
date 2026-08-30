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
"""Fixtures shared by the execution archive foundation tests."""

from pathlib import Path

import pytest

from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def sql_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqlZenStore:
    """Return a fresh SQLite-backed Zen store."""
    config_dir = tmp_path / "zenml-config"
    config_dir.mkdir()
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(config_dir))
    return SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{config_dir / 'zenml.db'}"
        ),
        skip_default_registrations=False,
    )
