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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for SQL store AWS RDS IAM authentication."""

import builtins
import ssl
from pathlib import Path
from typing import Any, Union, cast
from unittest.mock import MagicMock, call

import pymysql
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from pydantic import ValidationError
from sqlalchemy import create_engine

from zenml.enums import DatabaseBackupStrategy
from zenml.zen_stores.migrations.backup.sqlalchemy import (
    InMemoryDatabaseBackupEngine,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


def _iam_config(ca_file: Path, **kwargs: object) -> SqlZenStoreConfiguration:
    values = {
        "url": "mysql://db.example.com:3306/zenml0123456789abcdef0123456789abcdef",
        "username": "ws_abcdefghijklmnopqrstuvwxyz",
        "auth_mode": "aws_rds_iam",
        "aws_region": "eu-central-1",
        "ssl": True,
        "ssl_ca": str(ca_file),
        "ssl_verify_server_cert": True,
        "backup_strategy": DatabaseBackupStrategy.IN_MEMORY,
    }
    values.update(kwargs)
    return SqlZenStoreConfiguration(**values)


@pytest.fixture
def ca_file() -> Path:
    """Return the operating system CA bundle path."""
    path = ssl.get_default_verify_paths().cafile
    if path is None:
        pytest.skip("The test environment has no default CA bundle.")
    return Path(path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"aws_region": None}, "aws_region"),
        ({"password": "secret"}, "password"),
        ({"ssl": False}, "ssl=true"),
        ({"ssl_verify_server_cert": False}, "ssl_verify_server_cert=true"),
        ({"ssl_ca": None}, "explicit `ssl_ca`"),
    ],
)
def test_iam_configuration_rejects_unsafe_settings(
    ca_file: Path, overrides: dict[str, object], message: str
) -> None:
    """IAM mode rejects incomplete authentication and TLS settings."""
    with pytest.raises(ValidationError, match=message):
        _iam_config(ca_file, **overrides)


def test_password_mode_remains_the_default() -> None:
    """Existing password configuration retains its behavior."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml"
    )

    assert config.auth_mode == "password"
    assert config.password is not None


@pytest.mark.parametrize(
    "strategy",
    [
        DatabaseBackupStrategy.DATABASE,
        DatabaseBackupStrategy.MYDUMPER,
        DatabaseBackupStrategy.CUSTOM,
    ],
)
def test_iam_configuration_rejects_incompatible_backups(
    ca_file: Path, strategy: DatabaseBackupStrategy
) -> None:
    """IAM mode gates backup engines that need schema-global capabilities."""
    kwargs: dict[str, object] = {"backup_strategy": strategy}
    if strategy == DatabaseBackupStrategy.DATABASE:
        kwargs["backup_database"] = "backup"
    elif strategy == DatabaseBackupStrategy.CUSTOM:
        kwargs["custom_backup_engine"] = "example.BackupEngine"

    with pytest.raises(ValidationError, match="not supported"):
        _iam_config(ca_file, **kwargs)


@pytest.mark.parametrize(
    "strategy",
    [
        DatabaseBackupStrategy.DISABLED,
        DatabaseBackupStrategy.IN_MEMORY,
        DatabaseBackupStrategy.DUMP_FILE,
    ],
)
def test_iam_configuration_accepts_schema_scoped_backups(
    ca_file: Path, strategy: DatabaseBackupStrategy
) -> None:
    """IAM mode accepts backup strategies that stay in the primary schema."""
    assert _iam_config(ca_file, backup_strategy=strategy)


def _pymysql_ssl_context(
    ssl_args: Union[dict[str, Any], ssl.SSLContext],
) -> ssl.SSLContext:
    connection = pymysql.Connection(
        host="db.example.com",
        user="user",
        defer_connect=True,
        ssl=ssl_args,
    )
    context = getattr(connection, "ctx", None)
    assert context is not None
    return cast(ssl.SSLContext, context)


def test_password_default_ssl_preserves_unverified_context() -> None:
    """Default password SSL retains PyMySQL's historical verification mode."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml",
        ssl=True,
    )

    _, connect_args, _ = config.get_sqlalchemy_config()
    context = _pymysql_ssl_context(
        cast(Union[dict[str, Any], ssl.SSLContext], connect_args["ssl"])
    )

    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_password_ssl_with_ca_requires_certificate(ca_file: Path) -> None:
    """Password SSL with a CA retains PyMySQL certificate verification."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml",
        ssl=True,
        ssl_ca=str(ca_file),
    )

    _, connect_args, _ = config.get_sqlalchemy_config()
    context = _pymysql_ssl_context(
        cast(Union[dict[str, Any], ssl.SSLContext], connect_args["ssl"])
    )

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is False
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_iam_connect_args_use_verified_ssl_context(ca_file: Path) -> None:
    """MySQL connect args use a pre-built, verified SSLContext."""
    config = _iam_config(ca_file)

    _, connect_args, _ = config.get_sqlalchemy_config()

    context = connect_args["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert not isinstance(context, dict)
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_iam_missing_sdk_has_actionable_error(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IAM mode explains how to install its optional AWS SDK dependency."""
    config = _iam_config(ca_file)
    engine = create_engine("mysql+pymysql://user@db.example.com/db")
    real_import = builtins.__import__

    def import_without_boto3(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "boto3" or name.startswith("botocore"):
            raise ImportError("No module named 'boto3'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_boto3)

    with pytest.raises(ImportError, match=r"zenml\[aws-rds-iam\]"):
        config.configure_engine_auth(engine)


def test_iam_listener_binds_token_to_dialed_hostname(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listener generates a fresh token for the DBAPI connection target."""
    client = MagicMock()
    client.generate_db_auth_token.return_value = "token"
    monkeypatch.setattr("boto3.client", MagicMock(return_value=client))
    config = _iam_config(ca_file)
    engine = create_engine("mysql+pymysql://user@configured.example.com/db")
    config.configure_engine_auth(engine)
    params = {"host": "dialed.example.com", "port": 3307, "user": "ws_user"}

    engine.dialect.dispatch.do_connect(engine.dialect, None, [], params)

    assert params["password"] == "token"
    client.generate_db_auth_token.assert_called_once_with(
        DBHostname="dialed.example.com", Port=3307, DBUsername="ws_user"
    )


def test_iam_listener_retries_only_transient_errors(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listener retries transient transport errors but not authorization."""
    client = MagicMock()
    client.generate_db_auth_token.side_effect = [
        EndpointConnectionError(endpoint_url="https://rds"),
        "token",
    ]
    monkeypatch.setattr("boto3.client", MagicMock(return_value=client))
    sleep = MagicMock()
    monkeypatch.setattr("zenml.zen_stores.sql_zen_store.time.sleep", sleep)
    config = _iam_config(ca_file)
    engine = create_engine("mysql+pymysql://user@db.example.com/db")
    config.configure_engine_auth(engine)
    params = {"host": "db.example.com", "port": 3306, "user": "ws_user"}

    engine.dialect.dispatch.do_connect(engine.dialect, None, [], params)

    assert client.generate_db_auth_token.call_count == 2
    sleep.assert_called_once()

    client.generate_db_auth_token.reset_mock()
    client.generate_db_auth_token.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}},
        "GenerateDBAuthToken",
    )
    with pytest.raises(ClientError):
        engine.dialect.dispatch.do_connect(engine.dialect, None, [], params)
    client.generate_db_auth_token.assert_called_once()


def test_iam_listener_rejects_connection_without_tls_socket(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-connect listener rejects a DBAPI connection without live TLS."""
    monkeypatch.setattr("boto3.client", MagicMock())
    config = _iam_config(ca_file)
    engine = create_engine("mysql+pymysql://user@db.example.com/db")
    config.configure_engine_auth(engine)
    dbapi_connection = MagicMock()
    dbapi_connection._sock = None

    tls_listener = engine.pool.dispatch.connect.listeners[-1]
    with pytest.raises(RuntimeError, match="live TLS connection"):
        tls_listener(dbapi_connection, None)


def test_iam_mode_creates_missing_database(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IAM mode creates its configured schema when it does not exist."""
    config = _iam_config(ca_file)
    backup_engine = MagicMock()
    backup_engine.database_exists.return_value = False
    monkeypatch.setattr(
        SqlZenStore,
        "initialize_database_backup_engine",
        MagicMock(return_value=backup_engine),
    )
    monkeypatch.setattr(SqlZenStore, "_run_migrations", MagicMock())
    monkeypatch.setattr(SqlZenStore, "_initialize_database", MagicMock())
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.create_engine", MagicMock()
    )
    monkeypatch.setattr("zenml.zen_stores.sql_zen_store.Alembic", MagicMock())
    monkeypatch.setattr(
        SqlZenStoreConfiguration, "configure_engine_auth", MagicMock()
    )

    SqlZenStore(config=config)

    backup_engine.database_exists.assert_called_once_with()
    backup_engine.create_database.assert_called_once_with()


def test_iam_runtime_override_rejects_incompatible_backup(
    ca_file: Path,
) -> None:
    """Runtime strategy overrides cannot bypass IAM backup restrictions."""
    store = MagicMock()
    store.config = _iam_config(ca_file)

    with pytest.raises(ValueError, match="not supported"):
        SqlZenStore.initialize_database_backup_engine(
            store,
            strategy=DatabaseBackupStrategy.DATABASE,
            location="backup",
        )


@pytest.mark.parametrize(
    "strategy",
    [
        DatabaseBackupStrategy.DISABLED,
        DatabaseBackupStrategy.IN_MEMORY,
        DatabaseBackupStrategy.DUMP_FILE,
    ],
)
def test_iam_runtime_override_accepts_schema_scoped_backup(
    ca_file: Path, strategy: DatabaseBackupStrategy
) -> None:
    """Runtime overrides retain every schema-scoped IAM backup strategy."""
    store = MagicMock()
    store.config = _iam_config(ca_file)

    engine = SqlZenStore.initialize_database_backup_engine(
        store, strategy=strategy
    )

    assert engine is not None


def test_backup_engines_receive_iam_listener(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backup-created engines receive the same per-connection IAM auth hook."""
    config = _iam_config(ca_file)
    configure = MagicMock()
    monkeypatch.setattr(
        SqlZenStoreConfiguration, "configure_engine_auth", configure
    )
    backup = InMemoryDatabaseBackupEngine(config)

    engine = backup.create_engine(database=config.database)

    configure.assert_called_once_with(engine)


@pytest.mark.parametrize("auth_mode", ["password", "aws_rds_iam"])
def test_restore_database_replaces_existing_tables(
    auth_mode: str, ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restore replaces tables without recreating the schema in IAM mode."""
    config = (
        _iam_config(ca_file)
        if auth_mode == "aws_rds_iam"
        else SqlZenStoreConfiguration(
            url="mysql://user:secret@db.example.com:3306/zenml"  # ggignore
        )
    )
    backup = InMemoryDatabaseBackupEngine(config)
    backup.create_database = MagicMock()  # type: ignore[method-assign]
    connection = MagicMock()
    transaction = MagicMock()
    transaction.__enter__.return_value = connection
    engine = MagicMock()
    engine.begin.return_value = transaction
    backup._engine = engine
    existing_parent = MagicMock()
    existing_child = MagicMock()
    reflect_calls = 0

    def reflect(metadata: object, *, bind: object) -> None:
        nonlocal reflect_calls
        del bind
        reflect_calls += 1
        if reflect_calls == 1:
            metadata.sorted_tables = [  # type: ignore[attr-defined]
                existing_parent,
                existing_child,
            ]

    monkeypatch.setattr(
        "zenml.zen_stores.migrations.backup.sqlalchemy.MetaData.reflect",
        reflect,
    )

    backup.restore_database_from_storage()

    if auth_mode == "password":
        backup.create_database.assert_called_once_with(drop=True)
        existing_parent.drop.assert_not_called()
        existing_child.drop.assert_not_called()
    else:
        backup.create_database.assert_not_called()
        assert [
            existing_child.drop.call_args,
            existing_parent.drop.call_args,
        ] == [call(bind=connection), call(bind=connection)]
