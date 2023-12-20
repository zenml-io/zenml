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
import math
import os
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
    cast,
)
from uuid import UUID

from google.api_core import exceptions as google_exceptions
from google.cloud.secretmanager import SecretManagerServiceClient
from pydantic import root_validator

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import EntityExistsError
from zenml.integrations.gcp import (
    GCP_CONNECTOR_TYPE,
    GCP_RESOURCE_TYPE,
)
from zenml.integrations.gcp.service_connectors.gcp_service_connector import (
    GCPAuthenticationMethods,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.zen_stores.secrets_stores.service_connector_secrets_store import (
    ServiceConnectorSecretsStore,
    ServiceConnectorSecretsStoreConfiguration,
)

logger = get_logger(__name__)


GCP_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_GROUP_KEY = "zenml-group-key"
ZENML_GCP_SECRET_SCOPE_PATH_SEPARATOR = "-"
ZENML_GCP_DATE_FORMAT_STRING = "%Y-%m-%d-%H-%M-%S"
ZENML_GCP_SECRET_CREATED_KEY = "zenml-secret-created"
ZENML_GCP_SECRET_UPDATED_KEY = "zenml-secret-updated"


class GCPSecretsStoreConfiguration(ServiceConnectorSecretsStoreConfiguration):
    """GCP secrets store configuration.

    Attributes:
        type: The type of the store.
    """

    type: SecretsStoreType = SecretsStoreType.GCP

    @property
    def project_id(self) -> str:
        """Get the GCP project ID.

        Returns:
            The GCP project ID.

        Raises:
            ValueError: If the project ID is not set.
        """
        project_id = self.auth_config.get("project_id")
        if project_id:
            return str(project_id)

        raise ValueError("GCP `project_id` must be specified in auth_config.")

    @root_validator(pre=True)
    def populate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Populate the connector configuration from legacy attributes.

        Args:
            values: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.
        """
        # Search for legacy attributes and populate the connector configuration
        # from them, if they exist.
        if values.get("project_id") and os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        ):
            logger.warning(
                "The `project_id` GCP secrets store attribute and the "
                "`GOOGLE_APPLICATION_CREDENTIALS` environment variable are "
                "deprecated and will be removed in a future version of ZenML. "
                "Please use the `auth_method` and `auth_config` attributes "
                "instead."
            )
            values["auth_method"] = GCPAuthenticationMethods.SERVICE_ACCOUNT
            values["auth_config"] = dict(
                project_id=values.get("project_id"),
            )
            # Load the service account credentials from the file
            with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                values["auth_config"]["service_account_json"] = f.read()

        return values

    class Config:
        """Pydantic configuration class."""

        # Forbid extra attributes set in the class.
        extra = "allow"


class GCPSecretsStore(ServiceConnectorSecretsStore):
    """Secrets store implementation that uses the GCP Secrets Manager API."""

    config: GCPSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.GCP
    CONFIG_TYPE: ClassVar[
        Type[ServiceConnectorSecretsStoreConfiguration]
    ] = GCPSecretsStoreConfiguration
    SERVICE_CONNECTOR_TYPE: ClassVar[str] = GCP_CONNECTOR_TYPE
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str] = GCP_RESOURCE_TYPE

    _client: Optional[SecretManagerServiceClient] = None

    @property
    def client(self) -> SecretManagerServiceClient:
        """Initialize and return the GCP Secrets Manager client.

        Returns:
            The GCP Secrets Manager client instance.
        """
        return cast(SecretManagerServiceClient, super().client)

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the GCP Secrets Manager client from the service connector client.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The GCP Secrets Manager client.
        """
        return SecretManagerServiceClient(credentials=client)

    # ------
    # Secrets
    # ------

    @property
    def parent_name(self) -> str:
        """Construct the GCP parent path to the secret manager.

        Returns:
            The parent path to the secret manager
        """
        return f"projects/{self.config.project_id}"

    def _get_secret_labels(
        self, secret: Union[SecretRequestModel, SecretResponseModel]
    ) -> List[Tuple[str, str]]:
        """Return a list of Google secret label values for a given secret.

        Args:
            secret: the secret object

        Returns:
            A list of Google secret label values
        """
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
        values: Optional[Dict[str, str]] = None,
    ) -> SecretResponseModel:
        """Create a ZenML secret model from data stored in an GCP secret.

        If the GCP secret cannot be converted, the method acts as if the
        secret does not exist and raises a KeyError.

        Args:
            labels: The GCP secret labels.
            values: The GCP secret values.

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
            values=values,
        )

    def _get_gcp_filter_string(
        self, secret_filter_model: SecretFilterModel
    ) -> str:
        """Convert a SecretFilterModel to a GCP filter string.

        Args:
            secret_filter_model: The secret filter model.

        Returns:
            The GCP filter string.
        """
        operator_map = {
            "equals": ":",
        }
        filter_terms = []
        for filter in secret_filter_model.list_of_filters:
            filter_terms.append(
                f"{filter.column}{operator_map[filter.operation.value]}{filter.value}"
            )

        return f" {secret_filter_model.logical_operator.name} ".join(
            filter_terms
        )

    @track_decorator(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Create a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret: The secret to create.

        Returns:
            The created secret.

        Raises:
            RuntimeError: if the secret was unable to be created.
            EntityExistsError: If a secret with the same name already exists
                in the same scope.
        """
        self._validate_gcp_secret_name(secret.name)

        user, workspace = self._validate_user_and_workspace(
            secret.user, secret.workspace
        )

        # Check if a secret with the same name already exists in the same
        # scope.
        secret_exists, msg = self._check_secret_scope(
            secret_name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace,
            user=secret.user,
        )
        if secret_exists:
            raise EntityExistsError(msg)

        secret_id = uuid.uuid4()
        secret_value = json.dumps(secret.secret_values)

        created = datetime.utcnow().replace(tzinfo=None, microsecond=0)
        labels = self._get_secret_metadata_for_secret(
            secret=secret, secret_id=secret_id
        )
        labels[ZENML_GCP_SECRET_CREATED_KEY] = created.strftime(
            ZENML_GCP_DATE_FORMAT_STRING
        )
        labels[ZENML_GCP_SECRET_UPDATED_KEY] = created.strftime(
            ZENML_GCP_DATE_FORMAT_STRING
        )

        try:
            gcp_secret = self.client.create_secret(
                request={
                    "parent": self.parent_name,
                    "secret_id": self._get_gcp_secret_name(secret_id),
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": labels,
                    },
                }
            )

            logger.debug("Created empty parent secret: %s", gcp_secret.name)

            self.client.add_secret_version(
                request={
                    "parent": gcp_secret.name,
                    "payload": {"data": secret_value.encode()},
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create secret.: {str(e)}") from e

        logger.debug("Added value to secret.")

        return SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=workspace,
            user=user,
            values=secret.secret_values,
            created=created,
            updated=created,
        )

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.

        Raises:
            KeyError: If the secret does not exist.
            RuntimeError: If the GCP Secrets Manager API returns an unexpected
                error.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        try:
            secret = self.client.get_secret(name=gcp_secret_name)
            secret_version_values = self.client.access_secret_version(
                name=f"{gcp_secret_name}/versions/latest"
            )
        except google_exceptions.NotFound as e:
            raise KeyError(
                f"Can't find the specified secret for secret_id '{secret_id}': {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        secret_values = json.loads(
            secret_version_values.payload.data.decode("UTF-8")
        )

        return self._convert_gcp_secret(
            labels=secret.labels,
            values=secret_values,
        )

    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: The filter criteria.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.

        Raises:
            ValueError: If the filter contains an out-of-bounds page number.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        # TODO: implement filter method for server-side filtering
        # convert the secret_filter_model to a GCP filter string
        gcp_filters = ""
        # gcp_filters = self._get_gcp_filter_string(
        #     secret_filter_model=secret_filter_model
        # )

        try:
            # get all the secrets and their labels (for their names) from GCP
            # (use the filter string to limit what doesn't match the filter)
            secrets = []
            for secret in self.client.list_secrets(
                request={
                    "parent": self.parent_name,
                    "filter": gcp_filters,
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

        # do client filtering for anything not covered by the filter string
        filtered_secrets = [
            secret
            for secret in secrets
            if secret_filter_model.secret_matches(secret)
        ]

        # sort the results
        sorted_results = secret_filter_model.sort_secrets(filtered_secrets)

        # paginate the results
        secret_count = len(sorted_results)
        if secret_count == 0:
            total_pages = 1
        else:
            total_pages = math.ceil(secret_count / secret_filter_model.size)
        if secret_filter_model.page > total_pages:
            raise ValueError(
                f"Invalid page {secret_filter_model.page}. The requested page "
                f"size is {secret_filter_model.size} and there are a total of "
                f"{secret_count} items for this query. The maximum page value "
                f"therefore is {total_pages}."
            )
        return Page[SecretResponseModel](
            total=secret_count,
            total_pages=total_pages,
            items=sorted_results[
                (secret_filter_model.page - 1)
                * secret_filter_model.size : secret_filter_model.page
                * secret_filter_model.size
            ],
            index=secret_filter_model.page,
            max_size=secret_filter_model.size,
        )

    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdateModel
    ) -> SecretResponseModel:
        """Update a secret.

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
            secret_id: The ID of the secret to update.
            secret_update: The update to apply to the secret.

        Returns:
            The updated secret.

        Raises:
            RuntimeError: If the secret update is invalid.
            EntityExistsError: If the update includes a change of name or
                scope and a secret with the same name already exists in the
                same scope.
        """
        secret = self.get_secret(secret_id=secret_id)
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        assert secret.user is not None
        self._validate_user_and_workspace_update(
            secret_update=secret_update,
            current_user=secret.user.id,
            current_workspace=secret.workspace.id,
        )

        if secret_update.name is not None:
            self._validate_gcp_secret_name(secret_update.name)
            secret.name = secret_update.name
        if secret_update.scope is not None:
            secret.scope = secret_update.scope
        if secret_update.values is not None:
            # Merge the existing values with the update values.
            # The values that are set to `None` in the update are removed from
            # the existing secret when we call `.secret_values` later.
            secret.values.update(secret_update.values)

        if secret_update.name is not None or secret_update.scope is not None:
            # Check if a secret with the same name already exists in the same
            # scope.
            assert secret.user is not None
            secret_exists, msg = self._check_secret_scope(
                secret_name=secret.name,
                scope=secret.scope,
                workspace=secret.workspace.id,
                user=secret.user.id,
                exclude_secret_id=secret.id,
            )
            if secret_exists:
                raise EntityExistsError(msg)

        # Convert the ZenML secret metadata to GCP labels
        updated = datetime.utcnow().replace(tzinfo=None, microsecond=0)
        metadata = self._get_secret_metadata_for_secret(secret)
        metadata[ZENML_GCP_SECRET_UPDATED_KEY] = updated.strftime(
            ZENML_GCP_DATE_FORMAT_STRING
        )
        metadata[ZENML_GCP_SECRET_CREATED_KEY] = secret.created.strftime(
            ZENML_GCP_DATE_FORMAT_STRING
        )

        try:
            # UPDATE THE SECRET METADATA
            update_secret = {
                "name": gcp_secret_name,
                "labels": metadata,
            }
            update_mask = {"paths": ["labels"]}
            gcp_updated_secret = self.client.update_secret(
                request={
                    "secret": update_secret,
                    "update_mask": update_mask,
                }
            )
            # ADD A NEW SECRET VERSION
            secret_value = json.dumps(secret.secret_values)
            self.client.add_secret_version(
                request={
                    "parent": gcp_updated_secret.name,
                    "payload": {"data": secret_value.encode()},
                }
            )
        except Exception as e:
            raise RuntimeError(f"Error updating secret: {e}") from e

        logger.debug("Updated GCP secret: %s", gcp_secret_name)

        return SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace,
            user=secret.user,
            values=secret.secret_values,
            created=secret.created,
            updated=updated,
        )

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The ID of the secret to delete.

        Raises:
            KeyError: If the secret could not be found.
            RuntimeError: If the secret could not be deleted.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        try:
            self.client.delete_secret(request={"name": gcp_secret_name})
        except google_exceptions.NotFound:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to delete secret: {str(e)}") from e
