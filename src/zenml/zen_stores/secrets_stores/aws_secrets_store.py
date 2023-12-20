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
import math
import re
import time
import uuid
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

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.enums import (
    GenericFilterOps,
    LogicalOperators,
    SecretScope,
    SecretsStoreType,
)
from zenml.exceptions import EntityExistsError
from zenml.integrations.aws import (
    AWS_CONNECTOR_TYPE,
    AWS_RESOURCE_TYPE,
)
from zenml.integrations.aws.service_connectors.aws_service_connector import (
    AWSAuthenticationMethods,
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


AWS_ZENML_SECRET_NAME_PREFIX = "zenml"


class AWSSecretsStoreConfiguration(ServiceConnectorSecretsStoreConfiguration):
    """AWS secrets store configuration.

    Attributes:
        type: The type of the store.
        list_page_size: The number of secrets to fetch per page when
            listing secrets.
        secret_list_refresh_timeout: The number of seconds to wait after
            creating or updating an AWS secret until the changes are reflected
            in the secrets returned by `list_secrets`. Set this to zero to
            disable the wait. This may be necessary because it can take some
            time for new secrets and updated secrets to be reflected in the
            result returned by `list_secrets` on the client side. This value
            should not be set to a large value, because it blocks ZenML server
            threads while waiting and can cause performance issues.
            Disable this if you don't need changes to be reflected immediately
            on the client side.
    """

    type: SecretsStoreType = SecretsStoreType.AWS
    list_page_size: int = 100
    secret_list_refresh_timeout: int = 0

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

        # Forbid extra attributes set in the class.
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

    * the Secrets Store also makes heavy use of AWS secret tags to store all the
    metadata associated with a ZenML secret (e.g. the secret name, scope, user
    and workspace) and to filter secrets by these metadata. The `zenml` tag in
    particular is used to identify and group all secrets that belong to the same
    ZenML deployment.

    * all secret key-values configured in a ZenML secret are stored as a single
    JSON string value in the AWS secret value.

    * when a user or workspace is deleted, the secrets associated with it are
    deleted automatically via registered event handlers.


    Known challenges and limitations:

    * there is a known problem with the AWS Secrets Manager API that can cause
    the `list_secrets` method to return stale data for a long time (seconds)
    after a secret is created or updated. The AWS secrets store tries to
    mitigate this problem by waiting for a maximum configurable number of
    seconds after creating or updating a secret until the changes are reflected
    in the `list_secrets` AWS content. However, this is not a perfect solution,
    because it blocks ZenML server API threads while waiting. This can be
    disabled by setting the `secret_list_refresh_timeout` configuration
    parameter to zero.

    * only updating the secret values is reflected in the secret's `updated`
    timestamp. Updating the secret metadata (e.g. name, scope, user or
    workspace) does not update the secret's `updated` timestamp. This is a
    limitation of the AWS Secrets Manager API (updating AWS tags does not update
    the secret's `updated` timestamp).
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
    def _validate_aws_secret_name(name: str) -> None:
        """Validate a secret name.

        AWS secret names must contain only alphanumeric characters and the
        characters /_+=.@-. The `/` character is only used internally to
        implement the global namespace sharing scheme.

        Given that the ZenML secret name is stored as an AWS secret tag, the
        maximum value length is also restricted to 255 characters.

        Args:
            name: the secret name

        Raises:
            ValueError: if the secret name is invalid
        """
        if not re.fullmatch(r"[a-zA-Z0-9_+=\.@\-]*", name):
            raise ValueError(
                f"Invalid secret name '{name}'. Must contain only alphanumeric "
                f"characters and the characters _+=.@-."
            )

        if len(name) > 255:
            raise ValueError(
                f"Invalid secret name '{name}'. The maximum length is 255 "
                f"characters."
            )

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

    def _convert_aws_secret(
        self,
        tags: List[Dict[str, str]],
        created: datetime,
        updated: datetime,
        values: Optional[str] = None,
    ) -> SecretResponseModel:
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

    def _wait_for_secret_to_propagate(
        self, aws_secret_id: str, tags: List[Dict[str, str]]
    ) -> None:
        """Wait for an AWS secret to be refreshed in the list of secrets.

        The AWS Secrets Manager does not immediately reflect newly created
        and updated secrets in the `list_secrets` API. It is important that we
        wait for the secret to be refreshed in the `list_secrets` API
        before returning from create_secret/update_secret, otherwise the secret
        will not be available to the user. We also rely on `list_secrets`
        to enforce the scope rules, but given that the ZenML server runs
        requests in separate threads, it is not entirely possible to
        guarantee them.

        Args:
            aws_secret_id: The AWS secret ID.
            tags: The AWS secret tags that are expected to be present in the
                `list_secrets` response.
        """
        if self.config.secret_list_refresh_timeout <= 0:
            return

        # We wait for the secret to be available in the `list_secrets` API.
        for _ in range(self.config.secret_list_refresh_timeout):
            logger.debug(f"Waiting for secret {aws_secret_id} to be listed...")
            secret_exists = False
            try:
                secrets = self.client.list_secrets(
                    Filters=[{"Key": "name", "Values": [aws_secret_id]}]
                )
                if len(secrets["SecretList"]) > 0:
                    listed_secret = secrets["SecretList"][0]
                    # The supplied tags must exactly match those reported in the
                    # `list_secrets` response.
                    secret_exists = all(
                        tag in listed_secret["Tags"] for tag in tags
                    )
            except ClientError as e:
                logger.warning(
                    f"Error checking if secret {aws_secret_id} is listed: "
                    f"{e}. Retrying..."
                )

            if not secret_exists:
                logger.debug(
                    f"Secret {aws_secret_id} not yet listed. Retrying..."
                )
                time.sleep(1)
            else:
                logger.debug(f"Secret {aws_secret_id} listed.")
                break
        else:
            logger.warning(
                f"Secret {aws_secret_id} not updated in `list_secrets` "
                f"after {self.config.secret_list_refresh_timeout} seconds. "
            )

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
            EntityExistsError: If a secret with the same name already exists
                in the same scope.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        self._validate_aws_secret_name(secret.name)
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

        # Generate a new UUID for the secret
        secret_id = uuid.uuid4()
        aws_secret_id = self._get_aws_secret_id(secret_id)
        secret_value = json.dumps(secret.secret_values)

        # Convert the ZenML secret metadata to AWS tags
        metadata = self._get_secret_metadata_for_secret(
            secret, secret_id=secret_id
        )
        tags = self._get_aws_secret_tags(metadata)

        try:
            self.client.create_secret(
                Name=aws_secret_id,
                SecretString=secret_value,
                Tags=tags,
            )
            # We need a separate AWS API call to get the secret creation
            # date, since the create_secret API does not return it.
            describe_secret_response = self.client.describe_secret(
                SecretId=aws_secret_id
            )
        except ClientError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug("Created AWS secret: %s", aws_secret_id)

        self._wait_for_secret_to_propagate(aws_secret_id, tags=tags)

        secret_model = SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=workspace,
            user=user,
            values=secret.secret_values,
            created=describe_secret_response["CreatedDate"],
            updated=describe_secret_response["LastChangedDate"],
        )

        return secret_model

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.

        Raises:
            KeyError: If the secret does not exist.
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

        # The _convert_aws_secret method raises a KeyError if the
        # secret is tied to a workspace or user that no longer exists. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place, knowing that it will be cascade-deleted soon.
        return self._convert_aws_secret(
            tags=describe_secret_response["Tags"],
            created=describe_secret_response["CreatedDate"],
            updated=describe_secret_response["LastChangedDate"],
            values=get_secret_value_response["SecretString"],
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

        Raises:
            ValueError: If the filter contains an out-of-bounds page number.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        # The AWS Secrets Manager API does not natively support the entire
        # range of filtering, sorting and pagination options that ZenML
        # supports. The implementation of this method is therefore a bit
        # involved. We try to make use of the AWS filtering API as much as
        # possible to reduce the number of secrets that we need to fetch, then
        # we apply the rest of filtering, sorting and pagination on
        # the client side.

        metadata_args: Dict[str, Any] = {}
        if secret_filter_model.logical_operator == LogicalOperators.AND:
            # We can only filter on the AWS server side if we have an AND
            # logical operator. Otherwise, we need to filter on the client
            # side.

            for filter in secret_filter_model.list_of_filters:
                # The AWS Secrets Manager API only supports prefix matching. We
                # take advantage of this to filter as much as possible on the
                # AWS server side and we leave the rest to the client.
                if filter.operation not in [
                    GenericFilterOps.EQUALS,
                    GenericFilterOps.STARTSWITH,
                ]:
                    continue

                if filter.column == "id":
                    metadata_args["secret_id"] = UUID(filter.value)
                elif filter.column == "name":
                    metadata_args["secret_name"] = filter.value
                elif filter.column == "scope":
                    metadata_args["scope"] = SecretScope(filter.value)
                elif filter.column == "workspace_id":
                    metadata_args["workspace"] = UUID(filter.value)
                elif filter.column == "user_id":
                    metadata_args["user"] = UUID(filter.value)
                else:
                    # AWS doesn't support filtering on the created/updated
                    # timestamps, so we'll have to do that on the client side.
                    continue

        # The metadata will always contain at least the filter criteria
        # required to exclude everything but AWS secrets that belong to the
        # current ZenML deployment.
        metadata = self._get_secret_metadata(**metadata_args)
        aws_filters = self._get_aws_secret_filters(metadata)

        results: List[SecretResponseModel] = []

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
                    "PageSize": self.config.list_page_size,
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

                    # Filter again on the client side to cover all filter
                    # operations.
                    if not secret_filter_model.secret_matches(secret_model):
                        continue
                    results.append(secret_model)
        except ClientError as e:
            raise RuntimeError(f"Error listing AWS secrets: {e}")

        # Sort the results
        sorted_results = secret_filter_model.sort_secrets(results)

        # Paginate the results
        total = len(sorted_results)
        if total == 0:
            total_pages = 1
        else:
            total_pages = math.ceil(total / secret_filter_model.size)

        if secret_filter_model.page > total_pages:
            raise ValueError(
                f"Invalid page {secret_filter_model.page}. The requested page "
                f"size is {secret_filter_model.size} and there are a total of "
                f"{total} items for this query. The maximum page value "
                f"therefore is {total_pages}."
            )

        return Page[SecretResponseModel](
            total=total,
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
            EntityExistsError: If the update includes a change of name or
                scope and a secret with the same name already exists in the
                same scope.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        secret = self.get_secret(secret_id)

        # Prevent changes to the secret's user or workspace
        assert secret.user is not None
        self._validate_user_and_workspace_update(
            secret_update=secret_update,
            current_user=secret.user.id,
            current_workspace=secret.workspace.id,
        )

        if secret_update.name is not None:
            self._validate_aws_secret_name(secret_update.name)
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

        aws_secret_id = self._get_aws_secret_id(secret_id)
        secret_value = json.dumps(secret.secret_values)

        # Convert the ZenML secret metadata to AWS tags
        metadata = self._get_secret_metadata_for_secret(secret)
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
            # And another call to get the updated secret metadata which
            # includes the created and updated timestamps.
            describe_secret_response = self.client.describe_secret(
                SecretId=aws_secret_id
            )
        except ClientError as e:
            raise RuntimeError(f"Error updating secret: {e}")

        logger.debug("Updated AWS secret: %s", aws_secret_id)

        self._wait_for_secret_to_propagate(aws_secret_id, tags=tags)

        secret_model = SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace,
            user=secret.user,
            values=secret.secret_values,
            created=describe_secret_response["CreatedDate"],
            updated=describe_secret_response["LastChangedDate"],
        )

        return secret_model

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.

        Raises:
            KeyError: If the secret does not exist.
            RuntimeError: If the AWS Secrets Manager API returns an unexpected
                error.
        """
        try:
            self.client.delete_secret(
                SecretId=self._get_aws_secret_id(secret_id),
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
