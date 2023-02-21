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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, cast, Union

from google.api_core import exceptions as google_exceptions
from google.cloud import secretmanager

from zenml.exceptions import SecretExistsError
from zenml.integrations.gcp.flavors.gcp_secrets_manager_flavor import (
    GCPSecretsManagerConfig,
    validate_gcp_secret_name_or_namespace,
)
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import (
    ZENML_SECRET_NAME_LABEL,
    BaseSecretsManager,
    SecretsManagerScope,
)
from zenml.secrets_managers.utils import secret_from_dict, secret_to_dict


import json
import math
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
)
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from pydantic import SecretStr

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    GenericFilterOps,
    LogicalOperators,
    SecretScope,
    SecretsStoreType,
)
from zenml.exceptions import EntityExistsError
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
from zenml.secrets_managers.base_secrets_manager import ZENML_SECRET_NAME_LABEL
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

    @track(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Creates a new secret."""
        validate_gcp_secret_name_or_namespace(secret.name)

        secret_id = uuid.uuid4()
        secret_items = {
            k: json.dumps(v) for k, v in secret.secret_values.items()
        }

        for k, v in secret_items.items():
            gcp_secret = self.client.create_secret(
                request={
                    "parent": self.parent_name,
                    "secret_id": k,
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": self._get_secret_metadata_for_secret(
                            secret=secret, secret_id=secret_id
                        ),
                    },
                }
            )

            logger.debug("Created empty parent secret: %s", gcp_secret.name)

            self.client.add_secret_version(
                request={
                    "parent": gcp_secret.name,
                    "payload": {"data": str(v).encode()},
                }
            )

            logger.debug("Added value to secret.")

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.
        """
        google_secret_name = self.client.secret_path(
            self.config.project_id,
            f"{GCP_ZENML_SECRET_NAME_PREFIX}/{secret_id}",
        )

        try:
            # fetch the latest secret version
            google_secret = self.client.get_secret(name=google_secret_name)
        except google_exceptions.NotFound:
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        # make sure the secret has the correct scope labels to filter out
        # unscoped secrets with similar names
        scope_labels = self._get_secret_scope_metadata(secret_name)
        # all scope labels need to be included in the google secret labels,
        # otherwise the secret does not belong to the current scope
        if not scope_labels.items() <= google_secret.labels.items():
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        try:
            # fetch the latest secret version
            response = self.client.access_secret_version(
                name=f"{google_secret_name}/versions/latest"
            )
        except google_exceptions.NotFound:
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        secret_value = response.payload.data.decode("UTF-8")
        zenml_secret = secret_from_dict(
            json.loads(secret_value), secret_name=secret_name
        )
        return zenml_secret

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

    @track(AnalyticsEvent.DELETED_SECRET)
    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret."""
        pass
