#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Tests for ZenML global configuration behavior."""

import os
from collections.abc import Generator
from types import SimpleNamespace

import pytest

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX,
    ENV_ZENML_SECRETS_STORE_PREFIX,
)
from zenml.io import fileio
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)
from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration


@pytest.fixture(scope="module", autouse=True)
def auto_environment() -> Generator[
    tuple[SimpleNamespace, SimpleNamespace], None, None
]:
    """Use a lightweight test environment for global config unit tests."""
    yield SimpleNamespace(), SimpleNamespace()


def test_global_config_file_creation(clean_client):
    """Tests whether a config file gets created when the global config object is first instantiated."""
    if fileio.exists(GlobalConfiguration()._config_file):
        fileio.remove(GlobalConfiguration()._config_file)

    GlobalConfiguration._reset_instance()
    assert fileio.exists(GlobalConfiguration()._config_file)


def test_global_config_returns_value_from_environment_variable(
    mocker, clean_client
):
    """Tests that global config attributes can be overwritten by environment variables."""
    config = GlobalConfiguration()

    os.environ["ZENML_ANALYTICS_OPT_IN"] = "true"
    assert config.analytics_opt_in is True

    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
    assert config.analytics_opt_in is False


def test_sql_secret_previous_key_environment_variables(monkeypatch):
    """Tests SQL secrets-store previous-key env var import and export."""
    store_config = SqlZenStoreConfiguration(
        url="sqlite:///test.db",
        secrets_store=SqlSecretsStoreConfiguration(
            encryption_key="current-key",
            previous_encryption_key="previous-key",
        ),
        backup_secrets_store=SqlSecretsStoreConfiguration(
            encryption_key="backup-current-key",
            previous_encryption_key="backup-previous-key",
        ),
    )
    config = GlobalConfiguration.model_construct(store=store_config)

    environment_vars = config.get_config_environment_vars()

    assert (
        environment_vars[
            ENV_ZENML_SECRETS_STORE_PREFIX + "PREVIOUS_ENCRYPTION_KEY"
        ]
        == "previous-key"
    )
    assert (
        environment_vars[
            ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX + "PREVIOUS_ENCRYPTION_KEY"
        ]
        == "backup-previous-key"
    )

    monkeypatch.setenv(
        ENV_ZENML_SECRETS_STORE_PREFIX + "PREVIOUS_ENCRYPTION_KEY",
        "env-previous-key",
    )
    monkeypatch.setenv(
        ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX + "PREVIOUS_ENCRYPTION_KEY",
        "env-backup-previous-key",
    )

    resolved_config = config.get_store_configuration(baseline=store_config)

    assert (
        resolved_config.secrets_store.previous_encryption_key.get_secret_value()
        == "env-previous-key"
    )
    assert (
        resolved_config.backup_secrets_store.previous_encryption_key.get_secret_value()
        == "env-backup-previous-key"
    )

    monkeypatch.setenv(
        ENV_ZENML_SECRETS_STORE_PREFIX + "TYPE",
        "sql",
    )
    monkeypatch.setenv(
        ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX + "TYPE",
        "sql",
    )

    resolved_config = config.get_store_configuration(baseline=store_config)

    assert isinstance(
        resolved_config.secrets_store, SqlSecretsStoreConfiguration
    )
    assert (
        resolved_config.secrets_store.previous_encryption_key.get_secret_value()
        == "env-previous-key"
    )
    assert isinstance(
        resolved_config.backup_secrets_store, SqlSecretsStoreConfiguration
    )
    assert (
        resolved_config.backup_secrets_store.previous_encryption_key.get_secret_value()
        == "env-backup-previous-key"
    )
