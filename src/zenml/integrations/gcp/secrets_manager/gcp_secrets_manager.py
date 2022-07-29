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
"""Implementation of the GCP Secrets Manager."""

import re
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from google.cloud import secretmanager
from google.api_core import exceptions as google_exceptions
from pydantic import validator

from zenml.exceptions import SecretExistsError
from zenml.integrations.gcp import GCP_SECRETS_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import (
    ZENML_SCOPE_PATH_PREFIX,
    ZENML_SECRET_NAME_LABEL,
    BaseSecretsManager,
    SecretsManagerScope,
)
from zenml.secrets_managers.utils import secret_from_json, secret_to_json

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_GROUP_KEY = "zenml-group-key"


def remove_group_name_from_key(combined_key_name: str, group_name: str) -> str:
    """Removes the secret group name from the secret key.

    Args:
        combined_key_name: Full name as it is within the gcp secrets manager
        group_name: Group name (the ZenML Secret name)

    Returns:
        The cleaned key

    Raises:
        RuntimeError: If the group name is not found in the key
    """
    if combined_key_name.startswith(group_name + "_"):
        return combined_key_name[len(group_name + "_") :]
    else:
        raise RuntimeError(
            f"Key-name `{combined_key_name}` does not have the "
            f"prefix `{group_name}`. Key could not be "
            f"extracted."
        )


class GCPSecretsManager(BaseSecretsManager):
    """Class to interact with the GCP secrets manager.

    Attributes:
        project_id:  This is necessary to access the correct GCP project.
                     The project_id of your GCP project space that contains
                     the Secret Manager.
    """

    project_id: str

    # Class configuration
    FLAVOR: ClassVar[str] = GCP_SECRETS_MANAGER_FLAVOR
    SUPPORTS_SCOPING: ClassVar[bool] = True
    CLIENT: ClassVar[Any] = None

    @classmethod
    def _ensure_client_connected(cls) -> None:
        if cls.CLIENT is None:
            cls.CLIENT = secretmanager.SecretManagerServiceClient()

    @classmethod
    def _validate_scope(
        cls,
        scope: SecretsManagerScope,
        namespace: Optional[str],
    ) -> None:
        """Validate the scope and namespace value.

        Args:
            scope: Scope value.
        """
        if namespace:
            cls.validate_secret_name_or_namespace(namespace)

    @classmethod
    def validate_secret_name_or_namespace(
        cls,
        name: str,
    ) -> None:
        """Validate a secret name or namespace.

        A Google secret ID is a string with a maximum length of 255 characters
        and can contain uppercase and lowercase letters, numerals, and the
        hyphen (-) and underscore (_) characters. For scoped secrets, we have to
        limit the size of the name and namespace even further to allow space for
        both in the Google secret ID.

        Given that we also save secret names and namespaces as labels, we are
        also limited by the limitation that Google imposes on label values: max
        63 characters and must and must only contain lowercase letters, numerals
        and the hyphen (-) and underscore (_) characters

        Args:
            scope: the Secrets Manager scope
            name: the secret name or namespace

        Raises:
            ValueError: if the secret name or namespace is invalid
        """
        if not re.fullmatch(r"[a-z0-9_\-]+", name):
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. Must contain "
                f"only lowercase alphanumeric characters and the hyphen (-) and "
                f"underscore (_) characters."
            )

        if name and len(name) > 63:
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. The length is "
                f"limited to maximum 63 characters."
            )


    @property
    def parent_name(self) -> str:
        """Construct the GCP parent path to the secret manager.

        Returns:
            The parent path to the secret manager
        """
        return f"projects/{self.project_id}"

    def _get_scoped_secret_name(self, name: str) -> str:
        """Convert a ZenML secret name into a Google scoped secret name.

        Args:
            name: the name of the secret

        Returns:
            The Google scoped secret name
        """
        return "-".join(self._get_scoped_secret_path(name))

    def _get_unscoped_secret_name(self, name: str) -> Optional[str]:
        """Extract the name of a ZenML secret from a Google scoped secret name.

        Args:
            name: the name of the Google scoped secret

        Returns:
            The ZenML secret name or None, if the input secret name does not
            belong to the current scope.
        """
        return self._get_secret_name_from_path(name.split("-"))

    def _convert_secret_content(
        self, secret: BaseSecretSchema
    ) -> Dict[str, str]:
        """Convert the secret content into a Google compatible representation.

        This method implements two currently supported modes of adapting between
        the naming schemas used for ZenML secrets and Google secrets:

        * for a scoped Secrets Manager, a Google secret is created for each
        ZenML secret with a name that reflects the ZenML secret name and scope
        and a value that contains all its key-value pairs in JSON format.

        * for an unscoped (i.e. legacy) Secrets Manager, this method creates
        multiple Google secret entries for a single ZenML secret by adding the
        secret name to the key name of each secret key-value pair. This allows
        using the same key across multiple secrets. This is only kept for
        backwards compatibility and will be removed some time in the future.

        Args:
            secret: The ZenML secret

        Returns:
            A dictionary with the Google secret name as key and the secret
            contents as value.
        """
        if self.scope == SecretsManagerScope.NONE:
            # legacy per-key secret mapping
            return {f"{secret.name}_{k}": v for k, v in secret.content.items()}

        return {
            self._get_scoped_secret_name(secret.name): secret_to_json(secret),
        }

    def _get_secret_labels(
        self, secret: BaseSecretSchema
    ) -> List[Tuple[str, str]]:
        """Return a list of Google secret label values for a given secret.

        Args:
            secret: the secret object

        Returns:
            A list of Google secret label values
        """
        if self.scope == SecretsManagerScope.NONE:
            # legacy per-key secret labels
            return [
                (ZENML_GROUP_KEY, secret.name),
                (ZENML_SCHEMA_NAME, secret.TYPE),
            ]

        metadata = self._get_secret_metadata(secret)
        return list(metadata.items())

    def _get_secret_scope_filters(
        self,
        secret_name: Optional[str] = None,
    ) -> str:
        """Return a Google filter expression for the entire scope or just a scoped secret.

        These filters can be used when querying the Google Secrets Manager
        for all secrets or for a single secret available in the configured
        scope (see https://cloud.google.com/secret-manager/docs/filtering).

        Args:
            secret_name: Optional secret name to include in the scope metadata.

        Returns:
            Google filter expression uniquely identifying all secrets
            or a named secret within the configured scope.
        """
        if self.scope == SecretsManagerScope.NONE:
            # legacy per-key secret label filters
            if secret_name:
                return f"labels.{ZENML_GROUP_KEY}={secret_name}"
            else:
                return f"labels.{ZENML_GROUP_KEY}:*"

        metadata = self._get_secret_scope_metadata(secret_name)
        filters = [f"labels.{l}={v}" for (l, v) in metadata.items()]
        if secret_name:
            filters.append(f"name:{secret_name}")

        return " AND ".join(filters)

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
        """
        self.validate_secret_name_or_namespace(secret.name)
        self._ensure_client_connected()

        try:
            self.get_secret(secret.name)
            raise SecretExistsError(
                f"A Secret with the name {secret.name} already exists"
            )
        except KeyError:
            pass

        adjusted_content = self._convert_secret_content(secret)
        for k, v in adjusted_content.items():
            # Create the secret, this only creates an empty secret with the
            #  supplied name.
            gcp_secret = self.CLIENT.create_secret(
                request={
                    "parent": self.parent_name,
                    "secret_id": k,
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": self._get_secret_labels(secret),
                    },
                }
            )

            logger.debug("Created empty secret: %s", gcp_secret.name)

            self.CLIENT.add_secret_version(
                request={
                    "parent": gcp_secret.name,
                    "payload": {"data": str(v).encode()},
                }
            )

            logger.debug("Added value to secret.")

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Get a secret by its name.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist
        """
        self.validate_secret_name_or_namespace(secret_name)
        self._ensure_client_connected()

        zenml_secret: Optional[BaseSecretSchema] = None

        if self.scope == SecretsManagerScope.NONE:
            # Legacy secrets are mapped to multiple Google secrets, one for
            # each secret key

            secret_contents = {}
            zenml_schema_name = ""

            # List all secrets.
            for google_secret in self.CLIENT.list_secrets(
                request={
                    "parent": self.parent_name,
                    "filter": self._get_secret_scope_filters(secret_name),
                }
            ):
                secret_version_name = google_secret.name + "/versions/latest"

                response = self.CLIENT.access_secret_version(
                    request={"name": secret_version_name}
                )

                secret_value = response.payload.data.decode("UTF-8")

                secret_key = remove_group_name_from_key(
                    google_secret.name.split("/")[-1], secret_name
                )

                secret_contents[secret_key] = secret_value

                zenml_schema_name = google_secret.labels[ZENML_SCHEMA_NAME]

            if not secret_contents:
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )

            secret_contents["name"] = secret_name

            secret_schema = SecretSchemaClassRegistry.get_class(
                secret_schema=zenml_schema_name
            )
            zenml_secret = secret_schema(**secret_contents)

        else:
            # Scoped secrets are mapped 1-to-1 with Google secrets

            google_secret_name = "/".join(
                [
                    self.parent_name,
                    "secrets",
                    self._get_scoped_secret_name(secret_name),
                ]
            )

            try:
                # fetch the latest secret version
                google_secret = self.CLIENT.get_secret(
                    name=f"{google_secret_name}"
                )
            except google_exceptions.NotFound:
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )

            # make sure the secret has the correct scope labels to filter out
            # unscoped secrets with similar names
            scope_labels = self._get_secret_scope_metadata(secret_name)
            if not scope_labels.items() <= google_secret.labels.items():
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )

            try:
                # fetch the latest secret version
                response = self.CLIENT.access_secret_version(
                    name=f"{google_secret_name}/versions/latest"
                )
            except google_exceptions.NotFound:
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )

            secret_value = response.payload.data.decode("UTF-8")
            zenml_secret = secret_from_json(secret_value)

        return zenml_secret

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys
        """
        self._ensure_client_connected()

        set_of_secrets = set()

        # List all secrets.
        for secret in self.CLIENT.list_secrets(
            request={
                "parent": self.parent_name,
                "filter": self._get_secret_scope_filters(),
            }
        ):
            if self.scope == SecretsManagerScope.NONE:
                secret_name = secret.labels[ZENML_GROUP_KEY]
            else:
                secret_name = secret.labels[ZENML_SECRET_NAME_LABEL]
            set_of_secrets.add(secret_name)

        return list(set_of_secrets)

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret by creating new versions of the existing secrets.

        Args:
            secret: the secret to update
        """
        self.validate_secret_name_or_namespace(secret.name)
        self._ensure_client_connected()

        adjusted_content = self._convert_secret_content(secret)

        for k, v in adjusted_content.items():
            # Create the secret, this only creates an empty secret with the
            #  supplied name.
            version_parent = self.CLIENT.secret_path(self.project_id, k)
            payload = {"data": str(v).encode()}

            self.CLIENT.add_secret_version(
                request={"parent": version_parent, "payload": payload}
            )

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret by name.

        Args:
            secret_name: the name of the secret to delete

        Raises:
            KeyError: if the secret no longer exists
        """
        self.validate_secret_name_or_namespace(secret_name)
        self._ensure_client_connected()

        secret_deleted = False

        # Go through all gcp secrets and delete the ones with the secret_name
        # as label.
        for secret in self.CLIENT.list_secrets(
            request={
                "parent": self.parent_name,
                "filter": self._get_secret_scope_filters(secret_name),
            }
        ):
            secret_deleted = True
            self.CLIENT.delete_secret(request={"name": secret.name})

        if not secret_deleted:
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
        self._ensure_client_connected()

        # List all secrets.
        for secret in self.CLIENT.list_secrets(
            request={
                "parent": self.parent_name,
                "filter": self._get_secret_scope_filters(),
            }
        ):
            logger.info(f"Deleting Google secret {secret.name}")
            self.CLIENT.delete_secret(request={"name": secret.name})
