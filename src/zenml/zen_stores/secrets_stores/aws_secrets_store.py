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
"""AWS Secrets Store implementation."""

import json
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
)
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from pydantic import root_validator

from zenml.enums import (
    SecretsStoreType,
)
from zenml.integrations.aws import (
    AWS_CONNECTOR_TYPE,
    AWS_RESOURCE_TYPE,
)
from zenml.integrations.aws.service_connectors.aws_service_connector import (
    AWSAuthenticationMethods,
)
from zenml.logger import get_logger
from zenml.models import (
    SecretResponse,
)
from zenml.zen_stores.secrets_stores.service_connector_secrets_store import (
    ServiceConnectorSecretsStore,
    ServiceConnectorSecretsStoreConfiguration,
)

logger = get_logger(__name__)


AWS_ZENML_SECRET_NAME_PREFIX = "zenml"


class AWSSecretsStoreConfiguration(ServiceConnectorSecretsStoreConfiguration):
    """AWS secrets store configuration.

    Attributes:
        type: The type of the store.
    """

    type: SecretsStoreType = SecretsStoreType.AWS

    @property
    def region(self) -> str:
        """The AWS region to use.

        Returns:
            The AWS region to use.

        Raises:
            ValueError: If the region is not configured.
        """
        region = self.auth_config.get("region")
        if region:
            return str(region)

        raise ValueError("AWS `region` must be specified in the auth_config.")

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
        if (
            values.get("aws_access_key_id")
            and values.get("aws_secret_access_key")
            and values.get("region_name")
        ):
            logger.warning(
                "The `aws_access_key_id`, `aws_secret_access_key` and "
                "`region_name` AWS secrets store attributes are deprecated and "
                "will be removed in a future version of ZenML. Please use the "
                "`auth_method` and `auth_config` attributes instead."
            )
            values["auth_method"] = AWSAuthenticationMethods.SECRET_KEY
            values["auth_config"] = dict(
                aws_access_key_id=values.get("aws_access_key_id"),
                aws_secret_access_key=values.get("aws_secret_access_key"),
                region=values.get("region_name"),
            )

        return values

    class Config:
        """Pydantic configuration class."""

        # Allow extra attributes set in the class.
        extra = "allow"


class AWSSecretsStore(ServiceConnectorSecretsStore):
    """Secrets store implementation that uses the AWS Secrets Manager API.

    This secrets store implementation uses the AWS Secrets Manager API to
    store secrets. It allows a single AWS Secrets Manager region "instance" to
    be shared with other ZenML deployments as well as other third party users
    and applications.

    Here are some implementation highlights:

    * the name/ID of an AWS secret is derived from the ZenML secret UUID and a
    `zenml` prefix in the form `zenml/{zenml_secret_uuid}`. This clearly
    identifies a secret as being managed by ZenML in the AWS console.

    * the Secrets Store also uses AWS secret tags to store additional
    metadata associated with a ZenML secret. The `zenml` tag in particular is
    used to identify and group all secrets that belong to the same ZenML
    deployment.

    * all secret key-values configured in a ZenML secret are stored as a single
    JSON string value in the AWS secret value.
    """

    config: AWSSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.AWS
    CONFIG_TYPE: ClassVar[
        Type[ServiceConnectorSecretsStoreConfiguration]
    ] = AWSSecretsStoreConfiguration
    SERVICE_CONNECTOR_TYPE: ClassVar[str] = AWS_CONNECTOR_TYPE
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str] = AWS_RESOURCE_TYPE

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the AWS Secrets Manager client from the service connector client.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The AWS Secrets Manager client.
        """
        assert isinstance(client, boto3.Session)
        return client.client(
            "secretsmanager",
            region_name=self.config.region,
        )

    # ------
    # Secrets
    # ------

    @staticmethod
    def _get_aws_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the AWS secret ID corresponding to a ZenML secret ID.

        The convention used for AWS secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the AWS secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The AWS secret name.
        """
        return f"{AWS_ZENML_SECRET_NAME_PREFIX}/{str(secret_id)}"

    @staticmethod
    def _get_aws_secret_tags(
        metadata: Dict[str, str],
    ) -> List[Dict[str, str]]:
        """Convert ZenML secret metadata to AWS secret tags.

        Args:
            metadata: The ZenML secret metadata.

        Returns:
            The AWS secret tags.
        """
        aws_tags: List[Dict[str, str]] = []
        for k, v in metadata.items():
            aws_tags.append(
                {
                    "Key": k,
                    "Value": str(v),
                }
            )

        return aws_tags

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
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        aws_secret_id = self._get_aws_secret_id(secret_id)
        secret_value = json.dumps(secret_values)

        # Convert the ZenML secret metadata to AWS tags
        metadata = self._get_secret_metadata(secret_id=secret_id)
        tags = self._get_aws_secret_tags(metadata)

        try:
            self.client.create_secret(
                Name=aws_secret_id,
                SecretString=secret_value,
                Tags=tags,
            )
        except ClientError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug(f"Created AWS secret: {aws_secret_id}")

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        aws_secret_id = self._get_aws_secret_id(secret_id)

        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=aws_secret_id
            )
            # We need a separate AWS API call to get the AWS secret tags which
            # contain the ZenML secret metadata, since the get_secret_ value API
            # does not return them.
            describe_secret_response = self.client.describe_secret(
                SecretId=aws_secret_id
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise KeyError(f"Secret with ID {secret_id} not found")

            if (
                e.response["Error"]["Code"] == "InvalidRequestException"
                and "marked for deletion" in e.response["Error"]["Message"]
            ):
                raise KeyError(f"Secret with ID {secret_id} not found")

            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        # Convert the AWS secret tags to a metadata dictionary.
        metadata: Dict[str, str] = {
            tag["Key"]: tag["Value"]
            for tag in describe_secret_response["Tags"]
        }

        # The _verify_secret_metadata method raises a KeyError if the
        # secret is not valid or does not belong to this server. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place.
        self._verify_secret_metadata(
            secret_id=secret_id,
            metadata=metadata,
        )

        values = get_secret_value_response["SecretString"]

        logger.debug(f"Fetched AWS secret: {aws_secret_id}")

        secret_values = json.loads(values)

        if not isinstance(secret_values, dict):
            raise RuntimeError(
                f"AWS secret values for secret ID {aws_secret_id} could not be "
                "decoded: expected a dictionary."
            )

        return secret_values

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
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        aws_secret_id = self._get_aws_secret_id(secret_id)
        secret_value = json.dumps(secret_values)

        # Convert the ZenML secret metadata to AWS tags
        metadata = self._get_secret_metadata(secret_id)
        tags = self._get_aws_secret_tags(metadata)

        try:
            # One call to update the secret values
            self.client.put_secret_value(
                SecretId=aws_secret_id,
                SecretString=secret_value,
            )
            # Another call to update the tags
            self.client.tag_resource(
                SecretId=aws_secret_id,
                Tags=tags,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise KeyError(f"Secret with ID {secret_id} not found")
            raise RuntimeError(f"Error updating secret: {e}")

        logger.debug(f"Updated AWS secret: {aws_secret_id}")

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        aws_secret_id = self._get_aws_secret_id(secret_id)

        try:
            self.client.delete_secret(
                SecretId=aws_secret_id,
                # We set this to force immediate deletion of the AWS secret
                # instead of waiting for the recovery window to expire.
                ForceDeleteWithoutRecovery=True,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise KeyError(f"Secret with ID {secret_id} not found")

            if (
                e.response["Error"]["Code"] == "InvalidRequestException"
                and "marked for deletion" in e.response["Error"]["Message"]
            ):
                raise KeyError(f"Secret with ID {secret_id} not found")

            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )

        logger.debug(f"Deleted AWS secret: {aws_secret_id}")

    # ------------------------------------------------
    # Deprecated - kept only for migration from 0.53.0
    # ------------------------------------------------

    def _convert_aws_secret(
        self,
        tags: List[Dict[str, str]],
        created: datetime,
        updated: datetime,
        values: Optional[str] = None,
    ) -> SecretResponse:
        """Create a ZenML secret model from data stored in an AWS secret.

        If the AWS secret cannot be converted, the method acts as if the
        secret does not exist and raises a KeyError.

        Args:
            tags: The AWS secret tags.
            created: The AWS secret creation time.
            updated: The AWS secret last updated time.
            values: The AWS secret values encoded as a JSON string (optional).

        Returns:
            The ZenML secret.
        """
        # Convert the AWS secret tags to a metadata dictionary.
        metadata: Dict[str, str] = {tag["Key"]: tag["Value"] for tag in tags}

        return self._create_secret_from_metadata(
            metadata=metadata,
            created=created,
            updated=updated,
            values=json.loads(values) if values else None,
        )

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
    ) -> List[SecretResponse]:
        """List all secrets.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Returns:
            A list of all secrets.

        Raises:
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        # The metadata will always contain at least the filter criteria
        # required to exclude everything but AWS secrets that belong to the
        # current ZenML deployment.
        metadata = self._get_secret_metadata()
        aws_filters = self._get_aws_secret_filters(metadata)

        results: List[SecretResponse] = []

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
                        # NOTE: we do not include the secret values in the
                        # response. We would need a separate API call to fetch
                        # them for each secret, which would be very inefficient
                        # anyway.
                        secret_model = self._convert_aws_secret(
                            tags=secret["Tags"],
                            created=secret["CreatedDate"],
                            updated=secret["LastChangedDate"],
                        )
                    except KeyError:
                        # The _convert_aws_secret method raises a KeyError
                        # if the secret is tied to a workspace or user that no
                        # longer exists. Here we pretend that the secret does
                        # not exist.
                        continue

                    results.append(secret_model)
        except ClientError as e:
            raise RuntimeError(f"Error listing AWS secrets: {e}")

        return results
