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
"""Implementation of the GCP Secrets Store."""

import json
import re
import uuid
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from google.api_core import exceptions as google_exceptions
from google.cloud import secretmanager

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretScope,
    SecretsStoreType,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
    UserResponseModel,
    WorkspaceResponseModel,
)
from zenml.secrets_managers.base_secrets_manager import (
    ZENML_SECRET_NAME_LABEL,
)
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    ZENML_SECRET_ID_LABEL,
    ZENML_SECRET_SCOPE_LABEL,
    ZENML_SECRET_USER_LABEL,
    ZENML_SECRET_WORKSPACE_LABEL,
    BaseSecretsStore,
)

logger = get_logger(__name__)


logger = get_logger(__name__)

GCP_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_GROUP_KEY = "zenml-group-key"
ZENML_GCP_SECRET_SCOPE_PATH_SEPARATOR = "-"


class GCPSecretsStoreConfiguration(SecretsStoreConfiguration):
    """GCP secrets store configuration."""

    type: SecretsStoreType = SecretsStoreType.EXTERNAL
    project_id: str

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


class GCPSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the GCP Secrets Manager API."""

    config: GCPSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.EXTERNAL
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = GCPSecretsStoreConfiguration

    _client: Optional[Any] = None

    def _initialize(self) -> None:
        """Initialize the GCP secrets store."""
        logger.debug("Initializing GCPSecretsStore")

        # Initialize the GCP client.
        _ = self.client

    @property
    def zen_store(self) -> "BaseZenStore":
        """The ZenML store that owns this secrets store.

        Returns:
            The ZenML store that owns this secrets store.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._zen_store:
            raise ValueError("Store not initialized")
        return self._zen_store

    @property
    def client(self) -> Any:
        """Initialize and return the AWS Secrets Manager client.

        Returns:
            The AWS Secrets Manager client.
        """
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    @property
    def parent_name(self) -> str:
        """Construct the GCP parent path to the secret manager.

        Returns:
            The parent path to the secret manager
        """
        return f"projects/{self.config.project_id}"

    def _validate_user_and_workspace(
        self, user_id: UUID, workspace_id: UUID
    ) -> Tuple[UserResponseModel, WorkspaceResponseModel]:
        """Validates that the given user and workspace IDs are valid.

        This method calls the ZenML store to validate the user and workspace
        IDs. It raises a KeyError exception if either the user or workspace
        does not exist.

        Args:
            user_id: The ID of the user to validate.
            workspace_id: The ID of the workspace to validate.

        Returns:
            The user and workspace.
        """
        user = self.zen_store.get_user(user_id)
        workspace = self.zen_store.get_workspace(workspace_id)

        return user, workspace

    def _get_secret_labels(
        self, secret: Union[SecretRequestModel, SecretResponseModel]
    ) -> List[Tuple[str, str]]:
        """Return a list of Google secret label values for a given secret.

        Args:
            secret: the secret object

        Returns:
            A list of Google secret label values
        """
        # if self.config.scope == SecretsManagerScope.NONE:
        #     # legacy per-key secret labels
        #     return [
        #         (ZENML_GROUP_KEY, secret.name),
        #         (ZENML_SCHEMA_NAME, secret.TYPE),
        #     ]

        metadata = self._get_secret_metadata_for_secret(secret)
        return list(metadata.items())

    def _validate_gcp_secret_name(self, name: str) -> None:
        """Validate a secret name.

        Given that we save secret names as labels, we are also limited by the
        limitation that Google imposes on label values: max 63 characters and
        must only contain lowercase letters, numerals and the hyphen (-) and
        underscore (_) characters.

        Args:
            name: the secret name

        Raises:
            ValueError: if the secret name is invalid
        """
        if not re.fullmatch(r"[a-z0-9_\-]+", name):
            raise ValueError(
                f"Invalid secret name '{name}'. Must contain "
                f"only lowercase alphanumeric characters and the hyphen (-) and "
                f"underscore (_) characters."
            )

        if name and len(name) > 63:
            raise ValueError(
                f"Invalid secret name '{name}'. The length is "
                f"limited to maximum 63 characters."
            )

    def _check_secret_scope(
        self,
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
        filter = SecretFilterModel(
            name=secret_name,
            scope=scope,
            page=1,
            size=2,  # We only need to know if there is more than one secret
        )

        if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
            filter.workspace_id = workspace
        if scope == SecretScope.USER:
            filter.user_id = user

        existing_secrets = self.list_secrets(secret_filter_model=filter).items
        if exclude_secret_id is not None:
            existing_secrets = [
                s for s in existing_secrets if s.id != exclude_secret_id
            ]

        if existing_secrets:

            existing_secret_model = existing_secrets[0]

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

    def _get_gcp_secret_name(
        self,
        secret_id: UUID,
    ) -> str:
        """Get the GCP secret name for the given secret.

        The convention used for GCP secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the AWS secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The GCP secret name.
        """
        return f"{GCP_ZENML_SECRET_NAME_PREFIX}-{str(secret_id)}"

    def _convert_gcp_secret(
        self,
        labels: Dict[str, str],
        created: datetime,
        updated: datetime,
        values: Optional[Dict[str, str]] = None,
    ) -> SecretResponseModel:
        """Create a ZenML secret model from data stored in an GCP secret.

        Args:
            labels: The GCP secret labels.
            created: The GCP secret creation time.
            updated: The GCP secret last update time.
            values: The GCP secret values.

        Returns:
            The ZenML secret model.

        Raises:
            ValueError: if the GCP secret missing required tags.
            keyError: if the GCP secret was not found.
        """
        # Recover the ZenML secret metadata from the AWS secret tags.
        try:
            secret_id = UUID(labels[ZENML_SECRET_ID_LABEL])
            name = labels[ZENML_SECRET_NAME_LABEL]
            scope = SecretScope(labels[ZENML_SECRET_SCOPE_LABEL])
            workspace_id = UUID(labels[ZENML_SECRET_WORKSPACE_LABEL])
            user_id = UUID(labels[ZENML_SECRET_USER_LABEL])
        except KeyError as e:
            raise ValueError(
                f"Invalid GCP secret: missing required tag '{e}'"
            ) from e

        try:
            user, workspace = self._validate_user_and_workspace(
                user_id, workspace_id
            )
        except KeyError as e:
            # The user or workspace associated with the secret no longer
            # exists. This can happen if the user or workspace is being
            # deleted nearly at the same time as this call. In this case, we
            # raise a KeyError exception. The caller should handle this
            # exception by assuming that the secret no longer exists.
            logger.warning(
                f"Secret with ID '{secret_id}' is associated with a "
                f"non-existent user or workspace. Silently ignoring the "
                f"secret: {e}"
            )
            raise KeyError(f"Secret with ID {secret_id} not found") from e

        return SecretResponseModel(
            id=secret_id,
            name=name,
            scope=scope,
            workspace=workspace,
            user=user,
            values=values or {},
            created=created,
            updated=updated,
        )

    @track(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Create a new secret.

        Args:
            secret: The secret to create.

        Returns:
            The created secret.
        """
        self._validate_gcp_secret_name(secret.name)

        user, workspace = self._validate_user_and_workspace(
            secret.user, secret.workspace
        )

        # TODO: implement scope checks after list_secrets is implemented

        # Check if a secret with the same name already exists in the same
        # scope.
        # secret_exists, msg = self._check_secret_scope(
        #     secret_name=secret.name,
        #     scope=secret.scope,
        #     workspace=secret.workspace,
        #     user=secret.user,
        # )
        # if secret_exists:
        #     raise EntityExistsError(msg)

        secret_id = uuid.uuid4()
        secret_value = json.dumps(secret.secret_values)

        try:
            gcp_secret = self.client.create_secret(
                request={
                    "parent": self.parent_name,
                    "secret_id": f"{GCP_ZENML_SECRET_NAME_PREFIX}-{secret_id}",
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": self._get_secret_metadata_for_secret(
                            secret=secret, secret_id=secret_id
                        ),
                    },
                }
            )

            logger.debug("Created empty parent secret: %s", gcp_secret.name)

            gcp_secret_version = self.client.add_secret_version(
                request={
                    "parent": gcp_secret.name,
                    "payload": {"data": secret_value.encode()},
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create secret.: {str(e)}") from e

        logger.debug("Added value to secret.")

        secret_model = SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=workspace,
            user=user,
            values=secret.secret_values,
            created=gcp_secret.create_time,
            updated=gcp_secret_version.create_time,
        )

        print(secret_model)

        return secret_model

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        try:
            secret = self.client.get_secret(name=gcp_secret_name)
            secret_version = self.client.get_secret_version(
                name=f"{gcp_secret_name}/versions/latest"
            )
            secret_version_values = self.client.access_secret_version(
                name=f"{gcp_secret_name}/versions/latest"
            )
        except google_exceptions.NotFound as e:
            raise KeyError(
                f"Can't find the specified secret for secret_id '{secret_id}': {str(e)}"
            ) from e

        secret_values = json.loads(
            secret_version_values.payload.data.decode("UTF-8")
        )

        return self._convert_gcp_secret(
            labels=secret.labels,
            created=secret.create_time,
            updated=secret_version.create_time,
            values=secret_values,
        )

        # google_secret_name = self.client.secret_path(
        #     self.config.project_id,
        #     f"{GCP_ZENML_SECRET_NAME_PREFIX}/{secret_id}",
        # )

        # try:
        #     # fetch the latest secret version
        #     google_secret = self.client.get_secret(name=google_secret_name)
        # except google_exceptions.NotFound:
        #     raise KeyError(f"Can't find the specified secret '{secret_name}'")

        # # make sure the secret has the correct scope labels to filter out
        # # unscoped secrets with similar names
        # scope_labels = self._get_secret_scope_metadata(secret_name)
        # # all scope labels need to be included in the google secret labels,
        # # otherwise the secret does not belong to the current scope
        # if not scope_labels.items() <= google_secret.labels.items():
        #     raise KeyError(f"Can't find the specified secret '{secret_name}'")

        # try:
        #     # fetch the latest secret version
        #     response = self.client.access_secret_version(
        #         name=f"{google_secret_name}/versions/latest"
        #     )
        # except google_exceptions.NotFound:
        #     raise KeyError(f"Can't find the specified secret '{secret_name}'")

        # secret_value = response.payload.data.decode("UTF-8")
        # zenml_secret = secret_from_dict(
        #     json.loads(secret_value), secret_name=secret_name
        # )
        # return zenml_secret

    @track(AnalyticsEvent.DELETED_SECRET)
    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The ID of the secret to delete.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        # TODO: first check if the secret exists with the list method...

        try:
            self.client.delete_secret(request={"name": gcp_secret_name})
        except Exception as e:
            raise RuntimeError(f"Failed to delete secret: {str(e)}") from e

    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria."""
        pass

    @track(AnalyticsEvent.UPDATED_SECRET)
    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdateModel
    ) -> SecretResponseModel:
        """Updates a secret."""
        pass
