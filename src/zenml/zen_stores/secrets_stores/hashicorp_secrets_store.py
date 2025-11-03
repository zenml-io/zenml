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
"""HashiCorp Vault Secrets Store implementation."""

from datetime import datetime, timedelta
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
)
from uuid import UUID

import hvac
from hvac.constants.approle import (
    DEFAULT_MOUNT_POINT as APP_ROLE_DEFAULT_MOUNT_POINT,
)
from hvac.constants.aws import DEFAULT_MOUNT_POINT as AWS_DEFAULT_MOUNT_POINT
from hvac.exceptions import (
    InvalidPath,
    VaultError,
)
from pydantic import ConfigDict

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretsStoreType,
)
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)


HVAC_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_VAULT_SECRET_VALUES_KEY = "zenml_secret_values"
ZENML_VAULT_SECRET_METADATA_KEY = "zenml_secret_metadata"
DEFAULT_MOUNT_POINT = "secret"


class HashiCorpVaultAuthMethod(StrEnum):
    """HashiCorp Vault authentication methods."""

    TOKEN = "token"
    APP_ROLE = "app_role"
    AWS = "aws"


class HashiCorpVaultSecretsStoreConfiguration(SecretsStoreConfiguration):
    """HashiCorp Vault secrets store configuration.

    Attributes:
        type: The type of the store.
        vault_addr: The url of the Vault server. If not set, the value will be
            loaded from the VAULT_ADDR environment variable, if configured.
        vault_namespace: The Vault Enterprise namespace.
        mount_point: The mount point to use for all secrets.
        auth_method: The authentication method to use to authenticate with
            the Vault server.
        auth_mount_point: Custom mount point to use for the authentication
            method.
        vault_token: The token used to authenticate with the Vault server. If
            not set, the token will be loaded from the VAULT_TOKEN environment
            variable or from the ~/.vault-token file, if configured.
        app_role_id: The Vault role ID to use. Only used if the authentication
            method is APP_ROLE.
        app_secret_id: The Vault secret ID to use. Only used if the
            authentication method is APP_ROLE.
        aws_role: The AWS role to use. Only used if the authentication method is
            AWS.
        aws_header_value: The AWS header value to use. Only used if the
            authentication method is AWS and the mount point enforces it.
        max_versions: The maximum number of secret versions to keep.
    """

    type: SecretsStoreType = SecretsStoreType.HASHICORP
    vault_addr: str
    vault_namespace: Optional[str] = None
    mount_point: Optional[str] = None
    auth_method: HashiCorpVaultAuthMethod = HashiCorpVaultAuthMethod.TOKEN
    auth_mount_point: Optional[str] = None
    vault_token: Optional[PlainSerializedSecretStr] = None
    app_role_id: Optional[str] = None
    app_secret_id: Optional[str] = None
    aws_role: Optional[str] = None
    aws_header_value: Optional[str] = None
    max_versions: int = 1

    model_config = ConfigDict(extra="ignore")


class HashiCorpVaultSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the HashiCorp Vault API.

    This secrets store implementation uses the HashiCorp Vault API to
    store secrets. It allows a single HashiCorp Vault server to be shared with
    other ZenML deployments as well as other third party users and applications.

    Here are some implementation highlights:

    * the name/ID of an HashiCorp Vault secret is derived from the ZenML secret
    UUID and a `zenml` prefix in the form `zenml/{zenml_secret_uuid}`. This
    clearly identifies a secret as being managed by ZenML in the HashiCorp Vault
    server.

    * given that HashiCorp Vault secrets do not support attaching arbitrary
    metadata in the form of label or tags, we store the entire ZenML secret
    metadata alongside the secret values in the HashiCorp Vault secret value.

    Attributes:
        config: The configuration of the HashiCorp Vault secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: HashiCorpVaultSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.HASHICORP
    CONFIG_TYPE: ClassVar[Type[SecretsStoreConfiguration]] = (
        HashiCorpVaultSecretsStoreConfiguration
    )

    _client: Optional[hvac.Client] = None
    _expires_at: Optional[datetime] = None
    _renew_at: Optional[datetime] = None

    @property
    def client(self) -> hvac.Client:
        """Initialize and return the HashiCorp Vault client.

        Returns:
            The HashiCorp Vault client.

        Raises:
            ValueError: If the configuration is invalid.
        """

        def update_ttls(response: Dict[str, Any]) -> None:
            """Update the TTLs for the client.

            Args:
                response: The response from the HashiCorp Vault API.
            """
            expires_in = response.get("auth", {}).get("lease_duration")
            renewable = response.get("auth", {}).get("renewable", False)

            self._expires_at = None
            if expires_in:
                self._expires_at = datetime.now() + timedelta(
                    seconds=expires_in * 0.8  # 80% of the lease duration
                )

            self._renew_at = None
            if renewable and expires_in:
                self._renew_at = datetime.now() + timedelta(
                    seconds=expires_in * 0.5  # 50% of the lease duration
                )

        if (
            self._client
            and self._expires_at
            and self._expires_at < datetime.now()
        ):
            if self._renew_at and self._renew_at < datetime.now():
                logger.debug("Renewing token")
                try:
                    response = self._client.auth.token.renew_self()
                    update_ttls(response)
                except VaultError as e:
                    logger.warning(f"Error renewing token: {e}")
                    self._renew_at = None
                    self._expires_at = None
                    self._client = None
            else:
                self._client = None
                self._expires_at = None
                logger.debug("Token expired, re-authenticating")

        if self._client is None:
            self._client = hvac.Client(
                url=self.config.vault_addr,
                namespace=self.config.vault_namespace,
            )
            if self.config.auth_method == HashiCorpVaultAuthMethod.TOKEN:
                if not self.config.vault_token:
                    raise ValueError(
                        "A HashiCorp Vault token is required for token "
                        "authentication."
                    )
                self._client.token = self.config.vault_token.get_secret_value()
            elif self.config.auth_method == HashiCorpVaultAuthMethod.APP_ROLE:
                if (
                    not self.config.app_role_id
                    or not self.config.app_secret_id
                ):
                    raise ValueError(
                        "A HashiCorp Vault app role ID and secret ID are "
                        "required for app role authentication."
                    )
                response = self._client.auth.approle.login(
                    role_id=self.config.app_role_id,
                    secret_id=self.config.app_secret_id,
                    mount_point=self.config.auth_mount_point
                    or APP_ROLE_DEFAULT_MOUNT_POINT,
                )
                update_ttls(response)
            elif self.config.auth_method == HashiCorpVaultAuthMethod.AWS:
                import boto3

                sess = boto3.Session()
                creds = sess.get_credentials().get_frozen_credentials()

                response = self._client.auth.aws.iam_login(
                    access_key=creds.access_key,
                    secret_key=creds.secret_key,
                    session_token=creds.token,
                    role=self.config.aws_role,
                    header_value=self.config.aws_header_value,
                    mount_point=self.config.auth_mount_point
                    or AWS_DEFAULT_MOUNT_POINT,
                    use_token=True,
                )
                update_ttls(response)

            self._client.secrets.kv.v2.configure(
                mount_point=self.config.mount_point or DEFAULT_MOUNT_POINT,
                max_versions=self.config.max_versions,
            )

        return self._client

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the HashiCorp Vault secrets store."""
        logger.debug("Initializing HashiCorpVaultSecretsStore")

        # Initialize the HashiCorp Vault client early, just to catch any
        # configuration or authentication errors early, before the Secrets
        # Store is used.
        _ = self.client

    # ------
    # Secrets
    # ------

    @staticmethod
    def _get_vault_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the HashiCorp Vault secret ID corresponding to a ZenML secret ID.

        The convention used for HashiCorp Vault secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the HashiCorp Vault secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The HashiCorp Vault secret name.
        """
        return f"{HVAC_ZENML_SECRET_NAME_PREFIX}/{str(secret_id)}"

    def store_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Store secret values for a new secret.

        Args:
            secret_id: ID of the secret.
            secret_values: Values for the secret.

        Raises:
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                },
                # Do not allow overwriting an existing secret
                cas=0,
                mount_point=self.config.mount_point or DEFAULT_MOUNT_POINT,
            )
        except VaultError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug(f"Created HashiCorp Vault secret: {vault_secret_id}")

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        try:
            vault_secret = (
                self.client.secrets.kv.v2.read_secret(
                    path=vault_secret_id,
                    mount_point=self.config.mount_point or DEFAULT_MOUNT_POINT,
                )
                .get("data", {})
                .get("data", {})
            )
        except InvalidPath as e:
            raise KeyError(
                f"Can't find the secret values for secret ID '{secret_id}' "
                f"in the secrets store back-end: {str(e)}"
            ) from e
        except VaultError as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        try:
            metadata = vault_secret[ZENML_VAULT_SECRET_METADATA_KEY]
            values = vault_secret[ZENML_VAULT_SECRET_VALUES_KEY]
        except (KeyError, ValueError) as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        if not isinstance(values, dict) or not isinstance(metadata, dict):
            raise RuntimeError(
                f"HashiCorp Vault secret values for secret {vault_secret_id} "
                "could not be retrieved: invalid type for metadata or values"
            )

        # The _verify_secret_metadata method raises a KeyError if the
        # secret is not valid or does not belong to this server. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place.
        self._verify_secret_metadata(
            secret_id=secret_id,
            metadata=metadata,
        )

        logger.debug(f"Fetched HashiCorp Vault secret: {vault_secret_id}")

        return values

    def update_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Updates secret values for an existing secret.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_values: The new secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        # Convert the ZenML secret metadata to HashiCorp Vault tags
        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                },
                mount_point=self.config.mount_point or DEFAULT_MOUNT_POINT,
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(f"Error updating secret {secret_id}: {e}")

        logger.debug(f"Updated HashiCorp Vault secret: {vault_secret_id}")

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=vault_secret_id,
                mount_point=self.config.mount_point or DEFAULT_MOUNT_POINT,
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )

        logger.debug(f"Deleted HashiCorp Vault secret: {vault_secret_id}")
