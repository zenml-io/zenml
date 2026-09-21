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

from zenml.enums import DatabaseBackupStrategy, SQLDatabaseAuthMode
from zenml.zen_stores.migrations.backup.sqlalchemy import (
    DBCloneDatabaseBackupEngine,
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

    assert config.auth_mode == SQLDatabaseAuthMode.PASSWORD
    assert config.password is not None


def test_iam_connections_use_verified_system_trust() -> None:
    """IAM mode verifies both the certificate chain and hostname."""
    config = _iam_config()
    _, connect_args, _ = config.get_sqlalchemy_config()

    assert config.auth_mode == SQLDatabaseAuthMode.AWS_RDS_IAM
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


class _FakeClientError(Exception):
    """Stand-in for botocore's ClientError, which is an optional dependency."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def _iam_engine_connect(
    monkeypatch: pytest.MonkeyPatch,
    client: MagicMock,
    connect: MagicMock,
    sleep: MagicMock,
    **config: object,
) -> None:
    """Open one IAM-authenticated connection with a patched clock.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        client: Fake RDS client.
        connect: Fake database connection factory.
        sleep: Fake sleep function.
        **config: Store configuration overrides.
    """
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam._create_rds_client",
        MagicMock(return_value=client),
    )
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam.TLSRequiredMySQLConnection", connect
    )
    monkeypatch.setattr("zenml.zen_stores.rds_iam.time.sleep", sleep)
    engine = create_engine("mysql+pymysql://user@db.example.com/db")
    _iam_config(**config).configure_engine_auth(engine)
    engine.dialect.dispatch.do_connect(
        engine.dialect,
        None,
        [],
        {"host": "proxy.example.com", "port": 3306, "user": "ws_user"},
    )


def test_token_generation_waits_for_role_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A role that STS cannot see yet is retried with backoff."""
    client = MagicMock()
    client.generate_db_auth_token.side_effect = [
        _FakeClientError("AccessDenied"),
        _FakeClientError("InvalidIdentityToken"),
        "token",
    ]
    connect = MagicMock()
    sleep = MagicMock()

    _iam_engine_connect(monkeypatch, client, connect, sleep)

    assert sleep.call_args_list == [call(1.0), call(2.0)]
    connect.assert_called_once()


def test_connection_waits_for_connect_policy_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejected token is retried with a freshly generated one."""
    client = MagicMock()
    client.generate_db_auth_token.side_effect = ["first", "second"]
    connection = MagicMock()
    connect = MagicMock(
        side_effect=[
            pymysql.err.OperationalError(1045, "Access denied"),
            connection,
        ]
    )
    sleep = MagicMock()

    _iam_engine_connect(monkeypatch, client, connect, sleep)

    assert sleep.call_args_list == [call(1.0)]
    assert client.generate_db_auth_token.call_count == 2
    assert connect.call_args_list[-1].kwargs["password"] == "second"


@pytest.mark.parametrize(
    "error",
    [
        _FakeClientError("ValidationError"),
        pymysql.err.OperationalError(2003, "Can't connect"),
        RuntimeError("boom"),
    ],
)
def test_unrelated_errors_are_not_retried(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Only errors that IAM propagation can explain are retried."""
    client = MagicMock()
    connect = MagicMock(side_effect=error)
    sleep = MagicMock()

    with pytest.raises(type(error)):
        _iam_engine_connect(monkeypatch, client, connect, sleep)

    sleep.assert_not_called()
    connect.assert_called_once()


def test_propagation_wait_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A misconfigured role or user still fails within the wait budget."""
    client = MagicMock()
    client.generate_db_auth_token.side_effect = _FakeClientError(
        "AccessDenied"
    )
    sleep = MagicMock()

    with pytest.raises(_FakeClientError):
        _iam_engine_connect(
            monkeypatch,
            client,
            MagicMock(),
            sleep,
            aws_rds_iam_max_wait_seconds=2.5,
        )

    assert sleep.call_args_list == [call(1.0), call(1.5)]
    assert client.generate_db_auth_token.call_count == 3


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


def test_iam_supports_database_backup_strategy() -> None:
    """IAM mode supports a separately authorized backup database."""
    store = MagicMock()
    store.config = _iam_config(backup_database="zenml_backup")

    backup_engine = SqlZenStore.initialize_database_backup_engine(
        store, strategy=DatabaseBackupStrategy.DATABASE
    )

    assert isinstance(backup_engine, DBCloneDatabaseBackupEngine)
