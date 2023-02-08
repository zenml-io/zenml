#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""SQL Zen Store implementation."""

import base64
import json
from contextvars import ContextVar
from typing import (
    Any,
    ClassVar,
    Optional,
    Type,
    TypeVar,
    cast,
)
from uuid import UUID

import pymysql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound, OperationalError
from sqlmodel import Session, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import (
    BaseFilterModel,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.models.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models.page_model import Page
from zenml.models.secret_models import SecretScope
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.zen_stores.schemas import (
    BaseSchema,
    SecretSchema,
    NamedSchema,
    StackComponentSchema,
)
from zenml.zen_stores.secrets_stores.base_secrets_store import BaseSecretsStore
from zenml.zen_stores.sql_zen_store import SqlZenStore

AnyNamedSchema = TypeVar("AnyNamedSchema", bound=NamedSchema)
AnySchema = TypeVar("AnySchema", bound=BaseSchema)
B = TypeVar("B", bound=BaseResponseModel)

params_value: ContextVar[BaseFilterModel] = ContextVar("params_value")

logger = get_logger(__name__)


class SqlSecretsStoreConfiguration(SecretsStoreConfiguration):
    """SQL secrets store configuration.

    Attributes:
        type: The type of the store.
    """

    type: SecretsStoreType = SecretsStoreType.SQL

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
        _engine: The SQLAlchemy engine.
    """

    config: SqlSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.SQL
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = SqlSecretsStoreConfiguration

    _engine: Optional[Engine] = None
    _zen_store: Optional[SqlZenStore] = None

    def __init__(
        self,
        zen_store: SqlZenStore,
        **kwargs: Any,
    ) -> None:
        """Create and initialize the SQL secrets store.

        Args:
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.
        """
        self._zen_store = zen_store
        super().__init__(**kwargs)

    @property
    def engine(self) -> Engine:
        """The SQLAlchemy engine.

        Returns:
            The SQLAlchemy engine.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._engine:
            raise ValueError("Store not initialized")
        return self._engine

    @property
    def zen_store(self) -> SqlZenStore:
        """The ZenML store that this SQL secrets store is using as a back-end.

        Returns:
            The ZenML store that this SQL secrets store is using as a back-end.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._zen_store:
            raise ValueError("Store not initialized")
        return self._zen_store

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the secrets SQL store.

        Raises:
            OperationalError: If connecting to the database failed.
        """
        logger.debug("Initializing SqlSecretsStore")

        # Nothing to do here, the SQL ZenML store back-end is already
        # initialized

    # ------
    # Secrets
    # ------

    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Creates a new secret.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            EntityExistsError: If a secret with the same name already exists in
                this workspace.
            ValueError: In case the values contents exceeds the max length.
        """
        with Session(self.engine) as session:
            # Check if a secret with the same name already exists in the same
            # scope.
            scope_filter = select(SecretSchema).where(
                SecretSchema.name == secret.name
            )
            if secret.scope in [SecretScope.WORKSPACE, SecretScope.USER]:
                scope_filter = scope_filter.where(
                    SecretSchema.workspace_id == secret.workspace
                )
            if secret.scope == SecretScope.USER:
                scope_filter = scope_filter.where(
                    SecretSchema.user_id == secret.user
                )

            existing_secret = session.exec(scope_filter).first()

            if existing_secret is not None:
                msg = (
                    f"Unable to register secret with name '{secret.name}': "
                    f"Found an existing '{secret.scope.value}' scoped secret "
                    f"with the same name"
                )
                if secret.scope in [SecretScope.WORKSPACE, SecretScope.USER]:
                    msg += f" in the same '{secret.workspace}' workspace"
                if secret.scope == SecretScope.USER:
                    msg += f" for the same '{secret.user}' user"
                raise EntityExistsError(msg)

            serialized_values = base64.b64encode(
                json.dumps(secret.clear_values).encode("utf-8")
            )

            if len(serialized_values) > TEXT_FIELD_MAX_LENGTH:
                raise ValueError(
                    "Database representation of secret values exceeds max "
                    "length. Please use fewer values or consider using shorter "
                    "secret keys and/or values."
                )

            new_secret = SecretSchema.from_request(secret)
            session.add(new_secret)
            session.commit()

            return new_secret.to_model()

    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdateModel
    ) -> SecretResponseModel:
        """Updates an existing secret.

        Values that are specified as `None` in the update that are present in
        the existing secret will be removed from the existing secret. Values
        that are present in both secrets will be overwritten. All other values
        in both the existing secret and the update will be kept.

        Args:
            secret_id: The id of the secret to update.
            secret_update: The update to be applied to the secret.

        Returns:
            The updated secret.

        Raises:
            KeyError: If no secret with the given id exists.
        """
        with Session(self.engine) as session:
            existing_secret = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()

            if not existing_secret:
                raise KeyError(f"Secret with ID {secret_id} not found.")
            existing_secret.update(secret_update=secret_update)
            session.add(existing_secret)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_secret)
            return existing_secret.to_model()

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
            return secret_in_db.to_model()

    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria.

        Args:
            secret_filter_model: All filter parameters including pagination
                params

        Returns:
            List of all the secrets matching the given criteria.
        """
        with Session(self.engine) as session:
            query = select(SecretSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=SecretSchema,
                filter_model=secret_filter_model,
            )

    @track(AnalyticsEvent.DELETED_FLAVOR)
    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
            IllegalOperationError: if the secret is used by a stack component.
        """
        with Session(self.engine) as session:
            try:
                secret_in_db = session.exec(
                    select(SecretSchema).where(SecretSchema.id == secret_id)
                ).one()
                components_of_secret = session.exec(
                    select(StackComponentSchema).where(
                        StackComponentSchema.secret == secret_in_db.name
                    )
                ).all()
                if len(components_of_secret) > 0:
                    raise IllegalOperationError(
                        f"Stack Component `{secret_in_db.name}` of type "
                        f"`{secret_in_db.type} cannot be "
                        f"deleted as it is used by "
                        f"{len(components_of_secret)} "
                        f"components. Before deleting this "
                        f"secret, make sure to delete all "
                        f"associated components."
                    )
                else:
                    session.delete(secret_in_db)
            except NoResultFound as error:
                raise KeyError from error

    # =======================
    # Internal helper methods
    # =======================
