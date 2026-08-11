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
import importlib.util
import ssl
from pathlib import Path
from typing import Any, Union, cast
from unittest.mock import MagicMock

import pymysql
import pytest
from pydantic import ValidationError
from pymysql.constants import CLIENT
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from zenml.enums import DatabaseBackupStrategy
from zenml.zen_stores.migrations.backup.sqlalchemy import (
    InMemoryDatabaseBackupEngine,
)
from zenml.zen_stores.rds_iam import (
    TLSRequiredMySQLConnection,
    assert_verified_tls,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)

# boto3 ships in the `aws-rds-iam` extra, which a plain `pip install -e .[dev]`
# environment does not pull in. Importing it at module scope would take every
# test in this file down with it, so only the tests that drive the AWS SDK
# depend on it.
requires_aws_sdk = pytest.mark.skipif(
    importlib.util.find_spec("boto3") is None,
    reason="The AWS SDK (`zenml[aws-rds-iam]`) is not installed.",
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
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_iam_connect_args_use_verified_ssl_context(ca_file: Path) -> None:
    """MySQL connect args use a pre-built, verified SSLContext."""
    config = _iam_config(ca_file)

    _, connect_args, _ = config.get_sqlalchemy_config()

    context = connect_args["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT


def test_iam_ssl_context_pins_trust_to_the_configured_ca(
    tmp_path: Path,
) -> None:
    """The IAM context trusts only `ssl_ca`, not the system trust store."""
    ca_path = tmp_path / "rds-ca.pem"
    system_ca = ssl.get_default_verify_paths().cafile
    if system_ca is None:
        pytest.skip("The test environment has no default CA bundle.")
    # A single certificate lifted out of the system bundle stands in for the
    # RDS CA: the point is that pinning to it must not also carry over the
    # hundreds of other CAs the default context would otherwise trust.
    bundle = Path(system_ca).read_text()
    marker = "-----END CERTIFICATE-----"
    ca_path.write_text(bundle.split(marker)[0] + marker + "\n")

    config = SqlZenStoreConfiguration(
        url="mysql://db.example.com:3306/zenml0123456789abcdef0123456789abcdef",
        username="ws_abcdefghijklmnopqrstuvwxyz",
        auth_mode="aws_rds_iam",
        aws_region="eu-central-1",
        ssl=True,
        ssl_ca=str(ca_path),
        ssl_verify_server_cert=True,
    )

    _, connect_args, _ = config.get_sqlalchemy_config()

    context = cast(ssl.SSLContext, connect_args["ssl"])
    assert len(context.get_ca_certs()) == 1


def test_iam_ssl_ca_contents_are_accepted(ca_file: Path) -> None:
    """An inline PEM `ssl_ca` is written to disk and stays a secret string."""
    config = SqlZenStoreConfiguration(
        url="mysql://db.example.com:3306/zenml0123456789abcdef0123456789abcdef",
        username="ws_abcdefghijklmnopqrstuvwxyz",
        auth_mode="aws_rds_iam",
        aws_region="eu-central-1",
        ssl=True,
        ssl_ca=ca_file.read_text(),
        ssl_verify_server_cert=True,
    )

    _, connect_args, _ = config.get_sqlalchemy_config()

    assert isinstance(connect_args["ssl"], ssl.SSLContext)


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


@requires_aws_sdk
def test_iam_listener_binds_token_to_dialed_hostname(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listener generates a fresh token for the DBAPI connection target."""
    client = MagicMock()
    client.generate_db_auth_token.return_value = "token"
    monkeypatch.setattr("boto3.client", MagicMock(return_value=client))
    connection = MagicMock()
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam.TLSRequiredMySQLConnection",
        MagicMock(return_value=connection),
    )
    config = _iam_config(ca_file)
    engine = create_engine("mysql+pymysql://user@configured.example.com/db")
    config.configure_engine_auth(engine)
    params = {"host": "dialed.example.com", "port": 3307, "user": "ws_user"}

    engine.dialect.dispatch.do_connect(engine.dialect, None, [], params)

    assert params["password"] == "token"
    client.generate_db_auth_token.assert_called_once_with(
        DBHostname="dialed.example.com", Port=3307, DBUsername="ws_user"
    )


@requires_aws_sdk
def test_iam_authenticator_is_reused_across_engines(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All engines of a configuration share a single boto3 RDS client."""
    boto3_client = MagicMock()
    monkeypatch.setattr("boto3.client", boto3_client)
    config = _iam_config(ca_file)

    for _ in range(3):
        config.configure_engine_auth(
            create_engine("mysql+pymysql://user@db.example.com/db")
        )

    boto3_client.assert_called_once_with("rds", region_name="eu-central-1")


@requires_aws_sdk
def test_iam_listener_retries_only_transient_errors(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listener retries transient transport errors but not authorization."""
    from botocore.exceptions import ClientError, EndpointConnectionError

    client = MagicMock()
    client.generate_db_auth_token.side_effect = [
        EndpointConnectionError(endpoint_url="https://rds"),
        "token",
    ]
    monkeypatch.setattr("boto3.client", MagicMock(return_value=client))
    monkeypatch.setattr(
        "zenml.zen_stores.rds_iam.TLSRequiredMySQLConnection", MagicMock()
    )
    sleep = MagicMock()
    monkeypatch.setattr("zenml.zen_stores.rds_iam.time.sleep", sleep)
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


def test_iam_connection_refuses_to_authenticate_without_tls() -> None:
    """The token is never sent to a server that did not negotiate TLS."""
    connection = MagicMock(spec=TLSRequiredMySQLConnection)
    connection.ssl = True
    connection.server_capabilities = 0

    with pytest.raises(RuntimeError, match="unencrypted socket"):
        TLSRequiredMySQLConnection._request_authentication(connection)


def test_iam_connection_authenticates_once_tls_is_negotiated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The handshake proceeds when the server advertises TLS support."""
    authenticate = MagicMock(return_value="authenticated")
    monkeypatch.setattr(
        pymysql.Connection, "_request_authentication", authenticate
    )
    connection = MagicMock(spec=TLSRequiredMySQLConnection)
    connection.ssl = True
    connection.server_capabilities = CLIENT.SSL

    result = TLSRequiredMySQLConnection._request_authentication(connection)

    assert result == "authenticated"
    authenticate.assert_called_once()


def test_iam_post_connect_check_rejects_connection_without_tls_socket() -> (
    None
):
    """The post-connect check rejects a DBAPI connection without live TLS."""
    dbapi_connection = MagicMock()
    dbapi_connection._sock = None

    with pytest.raises(RuntimeError, match="live TLS connection"):
        assert_verified_tls(dbapi_connection)


def test_iam_post_connect_check_rejects_unverified_tls_socket() -> None:
    """The post-connect check rejects TLS without certificate verification."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    tls_socket = MagicMock(spec=ssl.SSLSocket)
    tls_socket.context = context
    tls_socket.server_hostname = "db.example.com"
    dbapi_connection = MagicMock()
    dbapi_connection._sock = tls_socket

    with pytest.raises(RuntimeError, match="verified TLS"):
        assert_verified_tls(dbapi_connection)


def _patch_store_initialization(
    monkeypatch: pytest.MonkeyPatch, backup_engine: MagicMock
) -> None:
    """Stub out everything `SqlZenStore._initialize` does besides the schema."""
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


def test_iam_mode_creates_missing_database(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IAM mode creates its configured schema when it does not exist."""
    config = _iam_config(ca_file)
    backup_engine = MagicMock()
    backup_engine.database_exists.return_value = False
    _patch_store_initialization(monkeypatch, backup_engine)

    SqlZenStore(config=config)

    backup_engine.database_exists.assert_called_once_with()
    backup_engine.create_database.assert_called_once_with()


@pytest.mark.parametrize("denied_on", ["database_exists", "create_database"])
def test_iam_mode_explains_missing_schema_privileges(
    ca_file: Path, denied_on: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A schema-scoped IAM user gets told to provision the schema itself.

    A user granted privileges on its own schema only is refused at whichever
    step it reaches first: MySQL answers `Access denied` (1044/1045) rather
    than `Unknown database` (1049) when probing, and refuses the master-engine
    `CREATE DATABASE` outright when it gets that far.
    """
    config = _iam_config(ca_file)
    backup_engine = MagicMock()
    backup_engine.database_exists.return_value = False
    denied = OperationalError(
        "SELECT 1", {}, Exception("Access denied for user")
    )
    getattr(backup_engine, denied_on).side_effect = denied
    _patch_store_initialization(monkeypatch, backup_engine)

    with pytest.raises(RuntimeError, match="must be provisioned") as exc_info:
        SqlZenStore(config=config)

    assert exc_info.value.__cause__ is denied


def test_password_mode_propagates_database_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Password mode keeps surfacing the original database error."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml"  # ggignore
    )
    backup_engine = MagicMock()
    backup_engine.database_exists.side_effect = OperationalError(
        "SELECT 1", {}, Exception("Access denied for user")
    )
    _patch_store_initialization(monkeypatch, backup_engine)

    with pytest.raises(OperationalError):
        SqlZenStore(config=config)


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


def _restore_backup_engine(
    config: SqlZenStoreConfiguration,
) -> tuple[InMemoryDatabaseBackupEngine, MagicMock]:
    """Build a backup engine whose restore runs against a mock connection."""
    backup = InMemoryDatabaseBackupEngine(config)
    backup.create_database = MagicMock()  # type: ignore[method-assign]
    connection = MagicMock()
    transaction = MagicMock()
    transaction.__enter__.return_value = connection
    engine = MagicMock()
    engine.begin.return_value = transaction
    backup._engine = engine
    return backup, connection


def _executed_statements(connection: MagicMock) -> list[str]:
    """Return the SQL text of every statement executed on a connection."""
    return [
        str(call_args.args[0])
        for call_args in connection.execute.mock_calls
        if call_args.args
    ]


def test_restore_drops_existing_tables_in_iam_mode(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IAM restore clears the schema in place instead of recreating it."""
    backup, connection = _restore_backup_engine(_iam_config(ca_file))
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["parent", "child"]
    monkeypatch.setattr(
        "zenml.zen_stores.migrations.backup.sqlalchemy.inspect",
        MagicMock(return_value=inspector),
    )

    backup.restore_database_from_storage()

    backup.create_database.assert_not_called()
    assert _executed_statements(connection) == [
        "SET FOREIGN_KEY_CHECKS = 0",
        "DROP TABLE IF EXISTS `parent`",
        "DROP TABLE IF EXISTS `child`",
        "SET FOREIGN_KEY_CHECKS = 1",
    ]


def test_restore_restores_foreign_key_checks_after_a_failed_drop(
    ca_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing DROP still re-enables foreign key checks on the connection."""
    backup, connection = _restore_backup_engine(_iam_config(ca_file))
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["parent"]
    monkeypatch.setattr(
        "zenml.zen_stores.migrations.backup.sqlalchemy.inspect",
        MagicMock(return_value=inspector),
    )
    connection.execute.side_effect = [
        None,
        Exception("lock wait timeout"),
        None,
    ]

    with pytest.raises(Exception, match="lock wait timeout"):
        backup.restore_database_from_storage()

    assert _executed_statements(connection)[-1] == "SET FOREIGN_KEY_CHECKS = 1"


def test_restore_recreates_the_database_in_password_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Password restore keeps dropping and recreating the whole database."""
    config = SqlZenStoreConfiguration(
        url="mysql://user:secret@db.example.com:3306/zenml"  # ggignore
    )
    backup, connection = _restore_backup_engine(config)
    inspect_mock = MagicMock()
    monkeypatch.setattr(
        "zenml.zen_stores.migrations.backup.sqlalchemy.inspect", inspect_mock
    )

    backup.restore_database_from_storage()

    backup.create_database.assert_called_once_with(drop=True)
    inspect_mock.assert_not_called()
    assert _executed_statements(connection) == []
