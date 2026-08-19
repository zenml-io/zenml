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
"""Tests for SQL store AWS RDS IAM authentication."""

import builtins
import ssl
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pymysql
import pytest
from pydantic import ValidationError
from pymysql.constants import CLIENT
from sqlalchemy import create_engine

from zenml.enums import DatabaseBackupStrategy
from zenml.zen_stores.migrations.backup.sqlalchemy import (
    InMemoryDatabaseBackupEngine,
)
from zenml.zen_stores.rds_iam import TLSRequiredMySQLConnection
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


def _iam_config(**kwargs: object) -> SqlZenStoreConfiguration:
    values = {
        "url": "mysql://db.example.com:3306/zenml",
        "username": "ws_user",
        "auth_mode": "aws_rds_iam",
        "aws_region": "eu-central-1",
        "ssl": True,
        "ssl_verify_server_cert": True,
        "backup_strategy": DatabaseBackupStrategy.IN_MEMORY,
    }
    values.update(kwargs)
    return SqlZenStoreConfiguration(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"aws_region": None}, "aws_region"),
        ({"password": "secret"}, "password"),
        ({"ssl": False}, "ssl=true"),
        ({"ssl_verify_server_cert": False}, "ssl_verify_server_cert=true"),
        ({"ssl_ca": "unused"}, "operating system trust store"),
    ],
)
def test_iam_configuration_rejects_unsafe_settings(
    overrides: dict[str, object], message: str
) -> None:
    """IAM mode rejects incomplete authentication and TLS settings."""
    with pytest.raises(ValidationError, match=message):
        _iam_config(**overrides)


def test_password_authentication_remains_the_default() -> None:
    """Existing password configurations retain their behavior."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml"
    )

    assert config.auth_mode == "password"
    assert config.password is not None


def test_iam_connections_use_verified_system_trust() -> None:
    """IAM mode verifies both the certificate chain and hostname."""
    _, connect_args, _ = _iam_config().get_sqlalchemy_config()

    context = connect_args["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_missing_aws_sdk_has_an_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IAM mode explains how to install its optional dependency."""
    real_import = builtins.__import__

    def import_without_boto3(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "boto3":
            raise ImportError("No module named 'boto3'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_boto3)

    with pytest.raises(ImportError, match=r"zenml\[aws-rds-iam\]"):
        _iam_config().configure_engine_auth(
            create_engine("mysql+pymysql://user@db.example.com/db")
        )


def test_each_connection_gets_a_fresh_token_for_its_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The engine signs every physical connection with its actual target."""
    client = MagicMock()
    client.generate_db_auth_token.side_effect = ["first", "second"]
    boto3 = SimpleNamespace(client=MagicMock(return_value=client))
    monkeypatch.setitem(sys.modules, "boto3", boto3)
    connect = MagicMock()
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam.TLSRequiredMySQLConnection", connect
    )
    engine = create_engine("mysql+pymysql://user@configured.example.com/db")
    _iam_config().configure_engine_auth(engine)

    first = {
        "host": "proxy.example.com",
        "port": 3307,
        "user": "ws_user",
    }
    second = dict(first)
    engine.dialect.dispatch.do_connect(engine.dialect, None, [], first)
    engine.dialect.dispatch.do_connect(engine.dialect, None, [], second)

    assert first["password"] == "first"
    assert second["password"] == "second"
    assert client.generate_db_auth_token.call_args_list == [
        call(DBHostname="proxy.example.com", Port=3307, DBUsername="ws_user"),
        call(DBHostname="proxy.example.com", Port=3307, DBUsername="ws_user"),
    ]
    assert connect.call_count == 2


def test_dedicated_database_role_is_used_for_iam_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IAM token generation uses the configured database-only role."""
    client = MagicMock()
    create_client = MagicMock(return_value=client)
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam._create_rds_client", create_client
    )
    engine = create_engine("mysql+pymysql://user@db.example.com/db")

    _iam_config(
        aws_rds_iam_role_arn="arn:aws:iam::123456789012:role/workspace-db"
    ).configure_engine_auth(engine)

    create_client.assert_called_once_with(
        "eu-central-1", "arn:aws:iam::123456789012:role/workspace-db"
    )


def test_connection_refuses_to_authenticate_without_tls() -> None:
    """The IAM token is not sent when the server does not negotiate TLS."""
    connection = MagicMock(spec=TLSRequiredMySQLConnection)
    connection.ssl = True
    connection.server_capabilities = 0

    with pytest.raises(RuntimeError, match="unencrypted connection"):
        TLSRequiredMySQLConnection._request_authentication(connection)


def test_connection_authenticates_after_tls_negotiation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The normal PyMySQL handshake runs once TLS is available."""
    authenticate = MagicMock(return_value="authenticated")
    monkeypatch.setattr(
        pymysql.Connection, "_request_authentication", authenticate
    )
    connection = MagicMock(spec=TLSRequiredMySQLConnection)
    connection.ssl = True
    connection.server_capabilities = CLIENT.SSL

    assert (
        TLSRequiredMySQLConnection._request_authentication(connection)
        == "authenticated"
    )
    authenticate.assert_called_once()


def test_backup_engines_receive_iam_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migration backup connections use the same IAM connection hook."""
    configure = MagicMock()
    monkeypatch.setattr(
        SqlZenStoreConfiguration, "configure_engine_auth", configure
    )
    backup = InMemoryDatabaseBackupEngine(_iam_config())

    engine = backup.create_engine(database="zenml")

    configure.assert_called_once_with(engine)


def test_iam_rejects_database_backup_strategy() -> None:
    """IAM mode rejects backups that require a second database."""
    store = MagicMock()
    store.config = _iam_config()

    with pytest.raises(ValueError, match="not supported"):
        SqlZenStore.initialize_database_backup_engine(
            store, strategy=DatabaseBackupStrategy.DATABASE
        )
