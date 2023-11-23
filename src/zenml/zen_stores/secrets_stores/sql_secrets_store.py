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

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Optional,
    Tuple,
    Type,
)
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine
from sqlmodel import Session, select

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretScope,
    SecretsStoreType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.zen_stores.schemas import (
    SecretSchema,
)
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore
    from zenml.zen_stores.sql_zen_store import SqlZenStore


class SqlSecretsStoreConfiguration(SecretsStoreConfiguration):
    """SQL secrets store configuration.

    Attributes:
        type: The type of the store.
        encryption_key: The encryption key to use for the SQL secrets store.
            If not set, the passwords will not be encrypted in the database.
    """

    type: SecretsStoreType = SecretsStoreType.SQL
    encryption_key: Optional[str] = None

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


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
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = SqlSecretsStoreConfiguration

    _encryption_engine: Optional[AesGcmEngine] = None

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

        # Initialize the encryption engine
        if self.config.encryption_key:
            self._encryption_engine = AesGcmEngine()
            self._encryption_engine._update_key(self.config.encryption_key)

        # Nothing else to do here, the SQL ZenML store back-end is already
        # initialized

    # ------
    # Secrets
    # ------

    def _check_sql_secret_scope(
        self,
        session: Session,
        secret_name: str,
        scope: SecretScope,
        workspace: UUID,
        user: UUID,
        exclude_secret_id: Optional[UUID] = None,
    ) -> Tuple[bool, str]:
        """Checks if a secret with the given name already exists in the given scope.

        This method enforces the following scope rules:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            session: The SQLAlchemy session.
            secret_name: The name of the secret.
            scope: The scope of the secret.
            workspace: The ID of the workspace to which the secret belongs.
            user: The ID of the user to which the secret belongs.
            exclude_secret_id: The ID of a secret to exclude from the check
                (used e.g. during an update to exclude the existing secret).

        Returns:
            True if a secret with the given name already exists in the given
            scope, False otherwise, and an error message.
        """
        scope_filter = (
            select(SecretSchema)
            .where(SecretSchema.name == secret_name)
            .where(SecretSchema.scope == scope.value)
        )

        if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
            scope_filter = scope_filter.where(
                SecretSchema.workspace_id == workspace
            )
        if scope == SecretScope.USER:
            scope_filter = scope_filter.where(SecretSchema.user_id == user)
        if exclude_secret_id is not None:
            scope_filter = scope_filter.where(
                SecretSchema.id != exclude_secret_id
            )

        existing_secret = session.exec(scope_filter).first()

        if existing_secret is not None:
            existing_secret_model = existing_secret.to_model(
                encryption_engine=self._encryption_engine
            )

            msg = (
                f"Found an existing {scope.value} scoped secret with the "
                f"same '{secret_name}' name"
            )
            if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
                msg += (
                    f" in the same '{existing_secret_model.workspace.name}' "
                    f"workspace"
                )
            if scope == SecretScope.USER:
                assert existing_secret_model.user
                msg += (
                    f" for the same '{existing_secret_model.user.name}' user"
                )

            return True, msg

        return False, ""

    @track_decorator(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Creates a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """
        with Session(self.engine) as session:
            # Check if a secret with the same name already exists in the same
            # scope.
            secret_exists, msg = self._check_sql_secret_scope(
                session=session,
                secret_name=secret.name,
                scope=secret.scope,
                workspace=secret.workspace,
                user=secret.user,
            )
            if secret_exists:
                raise EntityExistsError(msg)

            new_secret = SecretSchema.from_request(
                secret, encryption_engine=self._encryption_engine
            )
            session.add(new_secret)
            session.commit()

            return new_secret.to_model(
                encryption_engine=self._encryption_engine
            )

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.

        Raises:
            KeyError: if the secret doesn't exist.
        """
        with Session(self.engine) as session:
            secret_in_db = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()
            if secret_in_db is None:
                raise KeyError(f"Secret with ID {secret_id} not found.")
            return secret_in_db.to_model(
                encryption_engine=self._encryption_engine
            )

    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.
        """
        with Session(self.engine) as session:
            query = select(SecretSchema)
            return self.zen_store.filter_and_paginate(
                session=session,
                query=query,
                table=SecretSchema,
                filter_model=secret_filter_model,
                custom_schema_to_model_conversion=lambda secret: secret.to_model(
                    include_values=False
                ),
            )

    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdateModel
    ) -> SecretResponseModel:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).

        If the update includes a change of name or scope, the scoping rules
        enforced in the secrets store are used to validate the update:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """
        with Session(self.engine) as session:
            existing_secret = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()

            if not existing_secret:
                raise KeyError(f"Secret with ID {secret_id} not found.")

            # Prevent changes to the secret's user or workspace
            self._validate_user_and_workspace_update(
                secret_update=secret_update,
                current_user=existing_secret.user.id,
                current_workspace=existing_secret.workspace.id,
            )

            # A change in name or scope requires a check of the scoping rules.
            if (
                secret_update.name is not None
                and existing_secret.name != secret_update.name
                or secret_update.scope is not None
                and existing_secret.scope != secret_update.scope
            ):
                secret_exists, msg = self._check_sql_secret_scope(
                    session=session,
                    secret_name=secret_update.name or existing_secret.name,
                    scope=secret_update.scope
                    or SecretScope(existing_secret.scope),
                    workspace=secret_update.workspace
                    or existing_secret.workspace.id,
                    user=secret_update.user or existing_secret.user.id,
                    exclude_secret_id=secret_id,
                )

                if secret_exists:
                    raise EntityExistsError(msg)

            existing_secret.update(
                secret_update=secret_update,
                encryption_engine=self._encryption_engine,
            )
            session.add(existing_secret)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_secret)
            return existing_secret.to_model(
                encryption_engine=self._encryption_engine
            )

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
        """
        with Session(self.engine) as session:
            try:
                secret_in_db = session.exec(
                    select(SecretSchema).where(SecretSchema.id == secret_id)
                ).one()
                session.delete(secret_in_db)
                session.commit()
            except NoResultFound:
                raise KeyError(f"Secret with ID {secret_id} not found.")
