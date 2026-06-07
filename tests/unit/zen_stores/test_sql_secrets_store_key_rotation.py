"""Tests for SQL secrets-store key rotation compatibility."""

from collections.abc import Generator
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.zen_stores.schemas import SecretSchema
from zenml.zen_stores.schemas.secret_schemas import SecretDecodeError
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStore,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture(scope="module", autouse=True)
def auto_environment() -> Generator[
    tuple[SimpleNamespace, SimpleNamespace], None, None
]:
    """Use a lightweight test environment for SQL secrets-store unit tests."""
    yield SimpleNamespace(), SimpleNamespace()


def encryption_engine(key: str):
    """Create an AesGcmEngine through the SQL secrets-store helper."""
    return SqlSecretsStore._create_encryption_engine(
        PlainSerializedSecretStr(key)
    )


def secret_schema_with_values(
    *,
    values: dict[str, str],
    key: str,
) -> SecretSchema:
    """Create a SecretSchema with values encrypted by a specific key."""
    secret = SecretSchema(name="secret", private=False, user_id=None)
    secret.set_secret_values(values, encryption_engine=encryption_engine(key))
    return secret


def test_sql_secrets_store_can_read_with_previous_encryption_key() -> None:
    """Previous key fallback reads secrets encrypted before key rotation."""
    secret = secret_schema_with_values(
        values={"password": "old-value"},
        key="legacy-key",
    )
    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    assert store._get_secret_values_with_fallback(secret) == {
        "password": "old-value",
    }


def test_sql_secrets_store_prefers_current_encryption_key() -> None:
    """Current key remains the first read path for newly written secrets."""
    secret = secret_schema_with_values(
        values={"password": "new-value"},
        key="fresh-key",
    )
    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    assert store._get_secret_values_with_fallback(secret) == {
        "password": "new-value",
    }


def test_sql_secrets_store_raises_when_no_key_can_decrypt() -> None:
    """Fallback does not hide genuinely undecryptable secret rows."""
    secret = secret_schema_with_values(
        values={"password": "old-value"},
        key="unexpected-key",
    )
    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    with pytest.raises(SecretDecodeError):
        store._get_secret_values_with_fallback(secret)


def test_sql_secrets_store_reencrypts_previous_key_row() -> None:
    """Previous-key rows can be rewritten with the current key."""
    secret = secret_schema_with_values(
        values={"password": "old-value"},
        key="legacy-key",
    )
    original_values = secret.values
    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    assert store._reencrypt_secret_with_current_key(secret) is True
    assert secret.values != original_values
    assert secret.get_secret_values(
        encryption_engine=encryption_engine("fresh-key"),
    ) == {"password": "old-value"}


def test_sql_secrets_store_skips_current_key_row_reencryption() -> None:
    """Current-key rows are not rewritten during migration."""
    secret = secret_schema_with_values(
        values={"password": "new-value"},
        key="fresh-key",
    )
    original_values = secret.values
    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    assert store._reencrypt_secret_with_current_key(secret) is False
    assert secret.values == original_values


def test_sql_secrets_store_reencryption_noops_without_previous_key() -> None:
    """Migration is inactive unless a previous key is configured."""
    store = SqlSecretsStore.model_construct(
        _previous_encryption_engine=None,
    )

    stats = store.reencrypt_secrets_with_current_key()

    assert stats.scanned == 0
    assert stats.reencrypted == 0
    assert stats.skipped == 0
    assert stats.failed == 0


def test_sql_secrets_store_reencryption_requires_current_key() -> None:
    """Previous-key rows must not be rewritten without a current key."""
    secret = secret_schema_with_values(
        values={"password": "old-value"},
        key="legacy-key",
    )
    store = SqlSecretsStore.model_construct(
        _encryption_engine=None,
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    with pytest.raises(ValueError, match="current encryption key"):
        store._reencrypt_secret_with_current_key(secret)


def test_sql_secrets_store_reencryption_validates_limit() -> None:
    """Migration batch limits must be positive."""
    store = SqlSecretsStore.model_construct(
        _previous_encryption_engine=encryption_engine("legacy-key"),
    )

    with pytest.raises(ValueError, match="limit must be a positive integer"):
        store.reencrypt_secrets_with_current_key(limit=0)


def test_sql_secrets_store_reencryption_updates_database_rows() -> None:
    """Migration counters reflect real SQL row updates and commits."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    legacy_secret = secret_schema_with_values(
        values={"password": "old-value"},
        key="legacy-key",
    )
    legacy_secret.name = "legacy-secret"
    legacy_secret.user_id = user_id
    current_secret = secret_schema_with_values(
        values={"password": "new-value"},
        key="fresh-key",
    )
    current_secret.name = "current-secret"
    current_secret.user_id = user_id

    with Session(engine) as session:
        session.add(legacy_secret)
        session.add(current_secret)
        session.commit()

    store = SqlSecretsStore.model_construct(
        _encryption_engine=encryption_engine("fresh-key"),
        _previous_encryption_engine=encryption_engine("legacy-key"),
        _zen_store=SqlZenStore.model_construct(_engine=engine),
    )

    stats = store.reencrypt_secrets_with_current_key()

    assert stats.scanned == 2
    assert stats.reencrypted == 1
    assert stats.skipped == 1
    assert stats.failed == 0

    with Session(engine) as session:
        rows = {
            secret.name: secret
            for secret in session.exec(select(SecretSchema)).all()
        }

    assert rows["legacy-secret"].get_secret_values(
        encryption_engine=encryption_engine("fresh-key"),
    ) == {"password": "old-value"}
    assert rows["current-secret"].get_secret_values(
        encryption_engine=encryption_engine("fresh-key"),
    ) == {"password": "new-value"}
