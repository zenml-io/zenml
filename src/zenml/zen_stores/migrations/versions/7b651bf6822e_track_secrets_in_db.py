"""track secrets in db [7b651bf6822e].

Revision ID: 7b651bf6822e
Revises: 1ac1b9c04da1
Create Date: 2023-12-22 20:56:18.131906

"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from pydantic import BaseModel

from zenml.logger import get_logger

logger = get_logger(__name__)

# revision identifiers, used by Alembic.


revision = "7b651bf6822e"
down_revision = "1ac1b9c04da1"
branch_labels = None
depends_on = None


ZENML_SECRET_LABEL = "zenml"
ZENML_SECRET_ID_LABEL = "zenml_secret_id"
ZENML_SECRET_NAME_LABEL = "zenml_secret_name"
ZENML_SECRET_SCOPE_LABEL = "zenml_secret_scope"
ZENML_SECRET_USER_LABEL = "zenml_secret_user"
ZENML_SECRET_WORKSPACE_LABEL = "zenml_secret_workspace"


class ZenMLSecretMetadata(BaseModel):
    """ZenML secret metadata.

    This class reflects the structure of the ZenML secret metadata stored in the
    backend secret (e.g. in secret tags/labels) at the time when the secret
    metadata was migrated to the database. It is roughly aligned to the
    structure of the ZenML SecretResponse model as it was at that time.
    """

    id: UUID
    name: str
    user_id: UUID
    workspace_id: UUID
    created: datetime
    updated: datetime
    scope: str


class BaseSecretsStoreBackend(BaseModel):
    """Base class for accessing and listing ZenML secrets."""

    server_id: UUID
    client: Any = None

    def _get_secret_metadata(
        self,
        secret_id: Optional[UUID] = None,
    ) -> Dict[str, str]:
        """Get a dictionary with metadata that can be used as tags/labels.

        This utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The metadata can
        be configured alongside each secret.

        NOTE: the ZENML_SECRET_LABEL is always included in the metadata to
        distinguish ZenML secrets from other secrets that might be stored in
        the same backend, as well as to distinguish between different ZenML
        deployments using the same backend. Its value is set to the ZenML
        deployment ID.

        Args:
            secret_id: Optional secret ID to include in the metadata.

        Returns:
            Dictionary with secret metadata information.
        """
        # Always include the main ZenML label to distinguish ZenML secrets
        # from other secrets that might be stored in the same backend and
        # to distinguish between different ZenML deployments using the same
        # backend.
        metadata: Dict[str, str] = {ZENML_SECRET_LABEL: str(self.server_id)}

        # Include the secret ID if provided.
        if secret_id is not None:
            metadata[ZENML_SECRET_ID_LABEL] = str(secret_id)

        return metadata

    def _create_secret_from_metadata(
        self,
        metadata: Dict[str, str],
        created: datetime,
        updated: datetime,
    ) -> ZenMLSecretMetadata:
        """Create a ZenML secret metadata object from metadata stored in the secrets store backend.

        Args:
            metadata: ZenML secret metadata collected from the backend secret
                (e.g. from secret tags/labels).
            created: The secret creation time.
            updated: The secret last updated time.

        Returns:
            The ZenML secret.

        Raises:
            KeyError: If the secret does not have the required metadata, if it
                is not managed by this ZenML instance or if it is linked to a
                user or workspace that no longer exists.
        """
        # Double-check that the secret is managed by this ZenML instance.
        if metadata.get(ZENML_SECRET_LABEL) != str(self.server_id):
            raise KeyError("Secret is not managed by this ZenML instance")

        # Recover the ZenML secret fields from the input secret metadata.
        try:
            secret_id = UUID(metadata[ZENML_SECRET_ID_LABEL])
            name = metadata[ZENML_SECRET_NAME_LABEL]
            scope = metadata[ZENML_SECRET_SCOPE_LABEL]
            workspace_id = UUID(metadata[ZENML_SECRET_WORKSPACE_LABEL])
            user_id = UUID(metadata[ZENML_SECRET_USER_LABEL])
        except KeyError as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        secret_model = ZenMLSecretMetadata(
            id=secret_id,
            name=name,
            workspace_id=workspace_id,
            user_id=user_id,
            created=created,
            updated=updated,
            scope=scope,
        )

        return secret_model

    @abstractmethod
    def list_secrets(
        self,
    ) -> List[ZenMLSecretMetadata]:
        """List all ZenML secrets in the secrets store backend.

        Returns:
            A list of all secrets.
        """


class AWSSecretsStoreBackend(BaseSecretsStoreBackend):
    """AWS ZenML secrets store backend."""

    @staticmethod
    def _get_aws_secret_filters(
        metadata: Dict[str, str],
    ) -> List[Dict[str, str]]:
        """Convert ZenML secret metadata to AWS secret filters.

        Args:
            metadata: The ZenML secret metadata.

        Returns:
            The AWS secret filters.
        """
        aws_filters: List[Dict[str, Any]] = []
        for k, v in metadata.items():
            aws_filters.append(
                {
                    "Key": "tag-key",
                    "Values": [
                        k,
                    ],
                }
            )
            aws_filters.append(
                {
                    "Key": "tag-value",
                    "Values": [
                        str(v),
                    ],
                }
            )

        return aws_filters

    def list_secrets(
        self,
    ) -> List[ZenMLSecretMetadata]:
        """List all ZenML secrets in the AWS secrets store backend.

        Returns:
            A list of all secrets.

        Raises:
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        from botocore.exceptions import ClientError

        # The metadata will always contain at least the filter criteria
        # required to exclude everything but AWS secrets that belong to the
        # current ZenML deployment.
        metadata = self._get_secret_metadata()
        aws_filters = self._get_aws_secret_filters(metadata)

        results: List[ZenMLSecretMetadata] = []

        try:
            # AWS Secrets Manager API pagination is wrapped around the
            # `list_secrets` method call. We use it because we need to fetch all
            # secrets matching the (partial) filter that we set up. Note that
            # the pagination used here has nothing to do with the pagination
            # that we do for the method caller.
            paginator = self.client.get_paginator("list_secrets")
            pages = paginator.paginate(
                Filters=aws_filters,
                PaginationConfig={
                    "PageSize": 100,
                },
            )

            for page in pages:
                for secret in page["SecretList"]:
                    try:
                        # Convert the AWS secret tags to a metadata dictionary.
                        unpacked_metadata: Dict[str, str] = {
                            tag["Key"]: tag["Value"] for tag in secret["Tags"]
                        }

                        secret_model = self._create_secret_from_metadata(
                            metadata=unpacked_metadata,
                            created=secret["CreatedDate"],
                            updated=secret["LastChangedDate"],
                        )
                    except KeyError:
                        # The _convert_aws_secret method raises a KeyError
                        # if the secret is not well formed. Here we pretend that
                        # the secret does not exist.
                        continue

                    results.append(secret_model)
        except ClientError as e:
            raise RuntimeError(f"Error listing AWS secrets: {e}")

        return results


ZENML_GCP_DATE_FORMAT_STRING = "%Y-%m-%d-%H-%M-%S"
ZENML_GCP_SECRET_CREATED_KEY = "zenml-secret-created"
ZENML_GCP_SECRET_UPDATED_KEY = "zenml-secret-updated"


class GCPSecretsStoreBackend(BaseSecretsStoreBackend):
    """GCP ZenML secrets store backend."""

    project_id: str

    @property
    def parent_name(self) -> str:
        """Construct the GCP parent path to the secret manager.

        Returns:
            The parent path to the secret manager
        """
        return f"projects/{self.project_id}"

    def _convert_gcp_secret(
        self,
        labels: Dict[str, str],
    ) -> ZenMLSecretMetadata:
        """Create a ZenML secret model from data stored in an GCP secret.

        If the GCP secret cannot be converted, the method acts as if the
        secret does not exist and raises a KeyError.

        Args:
            labels: The GCP secret labels.

        Returns:
            The ZenML secret model.

        Raises:
            KeyError: if the GCP secret cannot be converted.
        """
        # Recover the ZenML secret metadata from the AWS secret tags.

        # The GCP secret labels do not really behave like a dictionary: when
        # a key is not found, it does not raise a KeyError, but instead
        # returns an empty string. That's why we make this conversion.
        label_dict = dict(labels)

        try:
            created = datetime.strptime(
                label_dict[ZENML_GCP_SECRET_CREATED_KEY],
                ZENML_GCP_DATE_FORMAT_STRING,
            )
            updated = datetime.strptime(
                label_dict[ZENML_GCP_SECRET_UPDATED_KEY],
                ZENML_GCP_DATE_FORMAT_STRING,
            )
        except KeyError as e:
            raise KeyError(
                f"Invalid GCP secret: missing required tag '{e}'"
            ) from e

        return self._create_secret_from_metadata(
            metadata=label_dict,
            created=created,
            updated=updated,
        )

    def list_secrets(self) -> List[ZenMLSecretMetadata]:
        """List all secrets.

        Returns:
            A list of all secrets.

        Raises:
            RuntimeError: if the GCP Secrets Manager API returns an unexpected
                error.
        """
        from google.cloud.secretmanager import SecretManagerServiceClient

        assert isinstance(self.client, SecretManagerServiceClient)

        try:
            # get all the secrets and their labels from GCP
            secrets = []
            for secret in self.client.list_secrets(
                request={
                    "parent": self.parent_name,
                    "filter": "",
                }
            ):
                try:
                    secrets.append(self._convert_gcp_secret(secret.labels))
                except KeyError:
                    # keep going / ignore if this secret version doesn't exist
                    # or isn't a ZenML secret
                    continue
        except Exception as e:
            raise RuntimeError(f"Error listing GCP secrets: {e}") from e

        return secrets


ZENML_AZURE_SECRET_CREATED_KEY = "zenml_secret_created"
ZENML_AZURE_SECRET_UPDATED_KEY = "zenml_secret_updated"


class AzureSecretsStoreBackend(BaseSecretsStoreBackend):
    """Azure ZenML secrets store backend."""

    def _convert_azure_secret(
        self,
        tags: Dict[str, str],
    ) -> ZenMLSecretMetadata:
        """Create a ZenML secret model from data stored in an Azure secret.

        If the Azure secret cannot be converted, the method acts as if the
        secret does not exist and raises a KeyError.

        Args:
            tags: The Azure secret tags.

        Returns:
            The ZenML secret.

        Raises:
            KeyError: if the Azure secret cannot be converted.
        """
        try:
            created = datetime.fromisoformat(
                tags[ZENML_AZURE_SECRET_CREATED_KEY],
            )
            updated = datetime.fromisoformat(
                tags[ZENML_AZURE_SECRET_UPDATED_KEY],
            )
        except KeyError as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        return self._create_secret_from_metadata(
            metadata=tags,
            created=created,
            updated=updated,
        )

    def list_secrets(self) -> List[ZenMLSecretMetadata]:
        """List all secrets.

        Returns:
            A list of all secrets.

        Raises:
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        from azure.core.exceptions import HttpResponseError
        from azure.keyvault.secrets import SecretClient

        assert isinstance(self.client, SecretClient)

        results: List[ZenMLSecretMetadata] = []

        try:
            all_secrets = self.client.list_properties_of_secrets()
            for secret_property in all_secrets:
                try:
                    # NOTE: we do not include the secret values in the
                    # response. We would need a separate API call to fetch
                    # them for each secret, which would be very inefficient
                    # anyway.
                    assert secret_property.tags is not None
                    secret_model = self._convert_azure_secret(
                        tags=secret_property.tags,
                    )
                except KeyError:
                    # The _convert_azure_secret method raises a KeyError
                    # if the secret is tied to a workspace or user that no
                    # longer exists or if it is otherwise not valid. Here we
                    # pretend that the secret does not exist.
                    continue

                results.append(secret_model)
        except HttpResponseError as e:
            raise RuntimeError(f"Error listing Azure Key Vault secrets: {e}")

        return results


HVAC_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_VAULT_SECRET_METADATA_KEY = "zenml_secret_metadata"
ZENML_VAULT_SECRET_CREATED_KEY = "zenml_secret_created"
ZENML_VAULT_SECRET_UPDATED_KEY = "zenml_secret_updated"


class HashiCorpVaultSecretsStoreBackend(BaseSecretsStoreBackend):
    """HashiCorp Vault ZenML secrets store backend."""

    def _convert_vault_secret(
        self,
        vault_secret: Dict[str, Any],
    ) -> ZenMLSecretMetadata:
        """Create a ZenML secret model from data stored in an HashiCorp Vault secret.

        If the HashiCorp Vault secret cannot be converted, the method acts as if
        the secret does not exist and raises a KeyError.

        Args:
            vault_secret: The HashiCorp Vault secret in JSON form.

        Returns:
            The ZenML secret.

        Raises:
            KeyError: if the HashiCorp Vault secret cannot be converted.
        """
        try:
            metadata = vault_secret[ZENML_VAULT_SECRET_METADATA_KEY]
            created = datetime.fromisoformat(
                vault_secret[ZENML_VAULT_SECRET_CREATED_KEY],
            )
            updated = datetime.fromisoformat(
                vault_secret[ZENML_VAULT_SECRET_UPDATED_KEY],
            )
        except (KeyError, ValueError) as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        return self._create_secret_from_metadata(
            metadata=metadata,
            created=created,
            updated=updated,
        )

    def list_secrets(self) -> List[ZenMLSecretMetadata]:
        """List all secrets.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Returns:
            A list of all secrets.

        Raises:
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        from hvac import Client  # type: ignore[import-untyped]
        from hvac.exceptions import (  # type: ignore[import-untyped]
            InvalidPath,
            VaultError,
        )

        assert isinstance(self.client, Client)

        results: List[ZenMLSecretMetadata] = []

        try:
            # List all ZenML secrets in the Vault
            all_secrets = (
                self.client.secrets.kv.v2.list_secrets(
                    path=HVAC_ZENML_SECRET_NAME_PREFIX
                )
                .get("data", {})
                .get("keys", [])
            )
        except InvalidPath:
            # no secrets created yet
            pass
        except VaultError as e:
            raise RuntimeError(f"Error listing HashiCorp Vault secrets: {e}")
        else:
            # Convert the Vault secrets to ZenML secrets
            for secret_uuid in all_secrets:
                vault_secret_id = (
                    f"{HVAC_ZENML_SECRET_NAME_PREFIX}/{secret_uuid}"
                )
                try:
                    vault_secret = (
                        self.client.secrets.kv.v2.read_secret(
                            path=vault_secret_id
                        )
                        .get("data", {})
                        .get("data", {})
                    )
                except (InvalidPath, VaultError) as e:
                    logger.warning(
                        f"Error fetching secret with ID {vault_secret_id}: {e}",
                    )
                    continue

                try:
                    secret_model = self._convert_vault_secret(
                        vault_secret,
                    )
                except KeyError as e:
                    # The _convert_vault_secret method raises a KeyError
                    # if the secret is not valid. Here we
                    # pretend that the secret does not exist.
                    logger.warning(
                        f"Error fetching secret with ID {vault_secret_id}: {e}",
                    )
                    continue

                results.append(secret_model)

        return results


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision.

    Raises:
        NotImplementedError: If the secrets store type is not supported.
    """
    from zenml.config.global_config import GlobalConfiguration
    from zenml.enums import SecretsStoreType
    from zenml.zen_stores.sql_zen_store import SqlZenStore

    logger.info("Migrating secrets from the external secrets store to the db.")

    store_cfg = GlobalConfiguration().store_configuration

    # We create a new SqlZenStore instance with the same configuration as the
    # one used to run migrations, but we skip the default registrations and
    # migrations. This is because we can't use the same store instance that is
    # used to run migrations because it would create an infinite loop.
    store = SqlZenStore(
        config=store_cfg,
        skip_default_registrations=True,
        skip_migrations=True,
    )

    secrets_store = store.secrets_store

    if secrets_store.TYPE == SecretsStoreType.SQL:
        # If the secrets store is already a SQL secrets store, we don't need
        # to transfer secrets from the external secrets store to the db.
        logger.info(
            "Skipping migration of secrets from the external secrets store "
            "to the db because the db is already configured as a SQL secrets "
            "store."
        )
        return

    logger.debug(
        f"Transferring secrets from the {secrets_store.type} secrets store "
        f"to the db: {secrets_store.config}"
    )

    # Transfer secrets from the external secrets store to the db

    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(
        only=("secret", "user", "workspace", "identity"), bind=op.get_bind()
    )
    secrets = sa.Table("secret", meta)
    users = sa.Table("user", meta)
    workspaces = sa.Table("workspace", meta)
    identity = sa.Table("identity", meta)

    # Extract the ZenML deployment ID from the identity table
    server_id = UUID(conn.execute(sa.select(identity.c.id)).scalar_one())

    # Initialize the secrets store backend based on the backend client extracted
    # from the secrets store.
    backend: BaseSecretsStoreBackend
    if secrets_store.TYPE == SecretsStoreType.AWS:
        from zenml.zen_stores.secrets_stores.aws_secrets_store import (
            AWSSecretsStore,
        )

        assert isinstance(secrets_store, AWSSecretsStore)
        backend = AWSSecretsStoreBackend(
            server_id=server_id,
            client=secrets_store.client,
        )
    elif secrets_store.TYPE == SecretsStoreType.GCP:
        from zenml.zen_stores.secrets_stores.gcp_secrets_store import (
            GCPSecretsStore,
        )

        assert isinstance(secrets_store, GCPSecretsStore)
        backend = GCPSecretsStoreBackend(
            server_id=server_id,
            client=secrets_store.client,
            project_id=secrets_store.config.project_id,
        )
    elif secrets_store.TYPE == SecretsStoreType.AZURE:
        from zenml.zen_stores.secrets_stores.azure_secrets_store import (
            AzureSecretsStore,
        )

        assert isinstance(secrets_store, AzureSecretsStore)
        backend = AzureSecretsStoreBackend(
            server_id=server_id,
            client=secrets_store.client,
        )
    elif secrets_store.TYPE == SecretsStoreType.HASHICORP:
        from zenml.zen_stores.secrets_stores.hashicorp_secrets_store import (
            HashiCorpVaultSecretsStore,
        )

        assert isinstance(secrets_store, HashiCorpVaultSecretsStore)
        backend = HashiCorpVaultSecretsStoreBackend(
            server_id=server_id,
            client=secrets_store.client,
        )
    else:
        raise NotImplementedError(
            f"Secrets store type {secrets_store.TYPE} not supported"
        )

    # List all secrets in the backend
    external_secrets = backend.list_secrets()
    if len(external_secrets) == 0:
        logger.debug("No secrets found in the external secrets store.")

    for secret in external_secrets:
        logger.info(
            f"Transferring secret '{secret.name}' from the "
            f"{secrets_store.type} secrets store to the db."
        )
        # Check if a user with the given ID exists in the db
        user = conn.execute(
            users.select().where(
                users.c.id == str(secret.user_id).replace("-", "")
            )
        ).first()
        if user is None:
            logger.warning(
                f"User with ID {secret.user_id} not found in the db. "
                f"Skipping secret '{secret.name}'."
            )
            continue
        # Check if a workspace with the given ID exists in the db
        workspace = conn.execute(
            workspaces.select().where(
                workspaces.c.id == str(secret.workspace_id).replace("-", "")
            )
        ).first()
        if workspace is None:
            logger.warning(
                f"Workspace with ID {secret.workspace_id} not found in the db. "
                f"Skipping secret '{secret.name}'."
            )
            continue

        # Check if there is already a secret with the same ID in the db
        # and delete it if there is. This can happen for example if the user has
        # previously migrated the secrets from the db to an external secrets
        # store and forgot to delete the secrets from the db.
        conn.execute(
            secrets.delete().where(
                secrets.c.id == str(secret.id).replace("-", "")
            )
        )
        conn.execute(
            secrets.insert().values(
                id=str(secret.id).replace("-", ""),
                created=secret.created,
                updated=secret.updated,
                name=secret.name,
                scope=secret.scope,
                values=None,
                workspace_id=str(secret.workspace_id).replace("-", ""),
                user_id=str(secret.user_id).replace("-", ""),
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
