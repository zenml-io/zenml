#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""SQL Secrets Store implementation."""

try:
    import sqlalchemy  # noqa
except ImportError:
    raise ImportError(
        "It seems like you've installed the `zenml` package without the "
        "`local` extra, but are trying to use ZenML with a local database.\n"
        "* If you want to use ZenML in a local setup, please install "
        "`zenml[local]` instead, e.g. using `pip install 'zenml[local]'`\n"
        "* If you want to connect to a server, run `zenml login`"
    ) from None

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
)
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine
from sqlmodel import Session, select

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import (
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.zen_stores.schemas import (
    SecretSchema,
)
from zenml.zen_stores.schemas.secret_schemas import SecretDecodeError
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore
    from zenml.zen_stores.sql_zen_store import SqlZenStore


@dataclass
class SqlSecretKeyMigrationStats:
    """Stats for SQL secrets-store key migration."""

    scanned: int = 0
    reencrypted: int = 0
    skipped: int = 0
    failed: int = 0

    def as_dict(self) -> Dict[str, int]:
        """Return stats as a JSON-serializable dictionary."""
        return {
            "scanned": self.scanned,
            "reencrypted": self.reencrypted,
            "skipped": self.skipped,
            "failed": self.failed,
        }


class SqlSecretsStoreConfiguration(SecretsStoreConfiguration):
    """SQL secrets store configuration.

    Attributes:
        type: The type of the store.
        encryption_key: The encryption key to use for the SQL secrets store.
            If not set, the passwords will not be encrypted in the database.
        previous_encryption_key: Previous encryption key to try when reading
            existing SQL secrets during a key rotation window. New or updated
            secrets are always written with `encryption_key`.
    """

    type: SecretsStoreType = SecretsStoreType.SQL
    encryption_key: Optional[PlainSerializedSecretStr] = None
    previous_encryption_key: Optional[PlainSerializedSecretStr] = None
    model_config = ConfigDict(
        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment=False,
        # Forbid extra attributes set in the class.
        extra="ignore",
    )


class SqlSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the SQL ZenML store as a backend.

    This secrets store piggybacks on the SQL ZenML store. It uses the same
    database and configuration as the SQL ZenML store.

    Attributes:
        config: The configuration of the SQL secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: SqlSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.SQL
    CONFIG_TYPE: ClassVar[Type[SecretsStoreConfiguration]] = (
        SqlSecretsStoreConfiguration
    )

    _encryption_engine: Optional[AesGcmEngine] = None
    _previous_encryption_engine: Optional[AesGcmEngine] = None

    def __init__(
        self,
        zen_store: "BaseZenStore",
        **kwargs: Any,
    ) -> None:
        """Create and initialize the SQL secrets store.

        Args:
            zen_store: The ZenML store that owns this SQL secrets store.
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.

        Raises:
            IllegalOperationError: If the ZenML store to which this secrets
                store belongs is not a SQL ZenML store.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStore

        if not isinstance(zen_store, SqlZenStore):
            raise IllegalOperationError(
                "The SQL secrets store can only be used with the SQL ZenML "
                "store."
            )
        super().__init__(zen_store, **kwargs)

    @property
    def engine(self) -> Engine:
        """The SQLAlchemy engine.

        Returns:
            The SQLAlchemy engine.
        """
        return self.zen_store.engine

    @property
    def zen_store(self) -> "SqlZenStore":
        """The ZenML store that this SQL secrets store is using as a back-end.

        Returns:
            The ZenML store that this SQL secrets store is using as a back-end.

        Raises:
            ValueError: If the store is not initialized.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStore

        if not self._zen_store:
            raise ValueError("Store not initialized")
        assert isinstance(self._zen_store, SqlZenStore)
        return self._zen_store

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the secrets SQL store."""
        logger.debug("Initializing SqlSecretsStore")

        # Initialize the encryption engines
        self._encryption_engine = self._create_encryption_engine(
            self.config.encryption_key
        )
        self._previous_encryption_engine = self._create_encryption_engine(
            self.config.previous_encryption_key
        )

        # Nothing else to do here, the SQL ZenML store back-end is already
        # initialized

    @staticmethod
    def _create_encryption_engine(
        encryption_key: Optional[PlainSerializedSecretStr],
    ) -> Optional[AesGcmEngine]:
        """Create an encryption engine for a configured SQL secrets key."""
        if not encryption_key:
            return None

        encryption_engine = AesGcmEngine()
        encryption_engine._update_key(encryption_key.get_secret_value())
        return encryption_engine

    def _read_encryption_engines(self) -> list[Optional[AesGcmEngine]]:
        """Return encryption engines to try when reading secret values."""
        engines = [self._encryption_engine]
        if self._previous_encryption_engine is not None:
            engines.append(self._previous_encryption_engine)
        return engines

    def _get_secret_values_with_fallback(
        self,
        secret_in_db: SecretSchema,
    ) -> Dict[str, str]:
        """Get secret values using the current key, then the previous key."""
        decode_error: Optional[SecretDecodeError] = None
        for encryption_engine in self._read_encryption_engines():
            try:
                return secret_in_db.get_secret_values(
                    encryption_engine=encryption_engine,
                )
            except SecretDecodeError as e:
                decode_error = e

        if decode_error:
            raise decode_error

        # This should be unreachable because `_read_encryption_engines` always
        # contains at least the current engine, even when it is None.
        return secret_in_db.get_secret_values(
            encryption_engine=self._encryption_engine,
        )

    def _reencrypt_secret_with_current_key(
        self,
        secret_in_db: SecretSchema,
    ) -> bool:
        """Re-encrypt one previous-key secret row with the current key."""
        if self._previous_encryption_engine is None:
            return False
        if self._encryption_engine is None:
            raise ValueError(
                "Cannot re-encrypt SQL secret rows without a current "
                "encryption key."
            )

        try:
            secret_in_db.get_secret_values(
                encryption_engine=self._encryption_engine,
            )
            return False
        except SecretDecodeError:
            secret_values = secret_in_db.get_secret_values(
                encryption_engine=self._previous_encryption_engine,
            )
            secret_in_db.set_secret_values(
                secret_values=secret_values,
                encryption_engine=self._encryption_engine,
            )
            return True

    def reencrypt_secrets_with_current_key(
        self,
        *,
        limit: Optional[int] = None,
        ignore_errors: bool = False,
    ) -> SqlSecretKeyMigrationStats:
        """Re-encrypt SQL secret rows that still require the previous key.

        Args:
            limit: Optional maximum number of secret rows to scan.
            ignore_errors: Whether to continue after an undecryptable row.

        Returns:
            Migration counters for scanned, re-encrypted, skipped, and failed
            secret rows.

        Raises:
            ValueError: If `limit` is not a positive integer.
            SecretDecodeError: If a row cannot be decrypted and
                `ignore_errors` is False.
        """
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer.")

        stats = SqlSecretKeyMigrationStats()
        if self._previous_encryption_engine is None:
            return stats

        with Session(self.engine) as session:
            query = select(SecretSchema)
            if limit is not None:
                query = query.limit(limit)

            secrets_in_db = session.exec(query).all()
            for secret_in_db in secrets_in_db:
                if not secret_in_db.values:
                    continue

                stats.scanned += 1
                try:
                    reencrypted = self._reencrypt_secret_with_current_key(
                        secret_in_db
                    )
                except SecretDecodeError:
                    stats.failed += 1
                    if not ignore_errors:
                        raise
                    continue

                if reencrypted:
                    stats.reencrypted += 1
                    session.add(secret_in_db)
                else:
                    stats.skipped += 1

            session.commit()

        return stats

    # ------
    # Secrets
    # ------

    def store_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Store secret values for a new secret.

        The secret is already created in the database by the SQL Zen store, this
        method only stores the secret values.

        Args:
            secret_id: ID of the secret.
            secret_values: Values for the secret.

        Raises:
            KeyError: if a secret for the given ID is not found.
        """
        with Session(self.engine) as session:
            secret_in_db = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()
            if secret_in_db is None:
                raise KeyError(f"Secret with ID {secret_id} not found.")
            secret_in_db.set_secret_values(
                secret_values=secret_values,
                encryption_engine=self._encryption_engine,
            )
            session.add(secret_in_db)
            session.commit()

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """
        with Session(self.engine) as session:
            secret_in_db = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()
            if secret_in_db is None:
                raise KeyError(f"Secret with ID {secret_id} not found.")
            try:
                return self._get_secret_values_with_fallback(secret_in_db)
            except SecretDecodeError:
                raise KeyError(
                    f"Secret values for secret {secret_id} could not be "
                    f"decoded. This can happen if encryption has "
                    f"been enabled/disabled or if the encryption key has been "
                    "reconfigured without proper secrets migration."
                )

    def update_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Updates secret values for an existing secret.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_values: The new secret values.
        """
        self.store_secret_values(secret_id, secret_values)

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """
        with Session(self.engine) as session:
            try:
                secret_in_db = session.exec(
                    select(SecretSchema).where(SecretSchema.id == secret_id)
                ).one()
                secret_in_db.values = None
                session.commit()
            except NoResultFound:
                raise KeyError(f"Secret with ID {secret_id} not found.")
