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
from functools import partial
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
from zenml.utils.pagination_utils import depaginate
from zenml.zen_stores.base_zen_store import BaseZenStore, StoreEvent
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    ZENML_SECRET_ID_LABEL,
    ZENML_SECRET_SCOPE_LABEL,
    ZENML_SECRET_USER_LABEL,
    ZENML_SECRET_WORKSPACE_LABEL,
    BaseSecretsStore,
)

logger = get_logger(__name__)


AWS_ZENML_SECRET_NAME_PREFIX = "zenml"


class AWSSecretsStoreConfiguration(SecretsStoreConfiguration):
    """AWS secrets store configuration.

    Attributes:
        type: The type of the store.
        region_name: The AWS region name to use.
        aws_access_key_id: The AWS access key ID to use to authenticate.
        aws_secret_access_key: The AWS secret access key to use to
            authenticate.
        aws_session_token: The AWS session token to use to authenticate.
        list_page_size: The number of secrets to fetch per page when
            listing secrets.
        secret_list_refresh_timeout: The number of seconds to wait after
            creating or updating an AWS secret until the changes are reflected
            in the secrets returned by `list_secrets`. Set this to zero to
            disable the wait. This is necessary because it can take some time
            for these changes to be reflected. This value should not be set to a
            large value, because it blocks ZenML server threads while waiting.
            Disable this if you don't need changes to be reflected immediately
            on the client side.
    """

    type: SecretsStoreType = SecretsStoreType.AWS
    region_name: str
    aws_access_key_id: Optional[SecretStr] = None
    aws_secret_access_key: Optional[SecretStr] = None
    aws_session_token: Optional[SecretStr] = None
    list_page_size: int = 100
    secret_list_refresh_timeout: int = 10

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


class AWSSecretsStore(BaseSecretsStore):
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


    Attributes:
        config: The configuration of the AWS secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: AWSSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.AWS
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = AWSSecretsStoreConfiguration

    _client: Optional[Any] = None

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

            # Initialize the AWS Secrets Manager client with the
            # credentials from the configuration, if provided.
            self._client = boto3.client(
                "secretsmanager",
                region_name=self.config.region_name,
                aws_access_key_id=self.config.aws_access_key_id.get_secret_value()
                if self.config.aws_access_key_id
                else None,
                aws_secret_access_key=self.config.aws_secret_access_key.get_secret_value()
                if self.config.aws_secret_access_key
                else None,
                aws_session_token=self.config.aws_session_token.get_secret_value()
                if self.config.aws_session_token
                else None,
            )
        return self._client

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the AWS secrets store."""
        logger.debug("Initializing AWSSecretsStore")

        # Initialize the AWS client early, just to catch any configuration or
        # authentication errors early, before the Secrets Store is used.
        _ = self.client

        self.zen_store.register_event_handler(
            StoreEvent.WORKSPACE_DELETED, self._on_workspace_deleted
        )

        self.zen_store.register_event_handler(
            StoreEvent.USER_DELETED, self._on_user_deleted
        )

    # --------------------
    # Store Event Handlers
    # --------------------

    def _on_workspace_deleted(
        self, event: StoreEvent, workspace_id: UUID
    ) -> None:
        """Handle the deletion of a workspace.

        This method deletes all secrets associated with the given workspace.

        Args:
            event: The store event.
            workspace_id: The ID of the workspace that was deleted.
        """
        logger.debug(
            "Handling workspace deletion event for workspace %s", workspace_id
        )

        # Delete all secrets associated with the workspace.
        secrets = depaginate(
            partial(
                self.list_secrets,
                secret_filter_model=SecretFilterModel(
                    workspace_id=workspace_id
                ),
            )
        )
        for secret in secrets:
            try:
                self.delete_secret(secret.id)
            except KeyError:
                pass
            except Exception as e:
                logger.warning("Failed to delete secret %s: %s", secret.id, e)

    def _on_user_deleted(self, event: StoreEvent, user_id: UUID) -> None:
        """Handle the deletion of a user.

        This method deletes all secrets associated with the given user.

        Args:
            event: The store event.
            user_id: The ID of the user that was deleted.
        """
        logger.debug("Handling user deletion event for user %s", user_id)

        # Delete all secrets associated with the user.
        secrets = depaginate(
            partial(
                self.list_secrets,
                secret_filter_model=SecretFilterModel(user_id=user_id),
            )
        )
        for secret in secrets:
            try:
                self.delete_secret(secret.id)
            except KeyError:
                pass
            except Exception as e:
                logger.warning("Failed to delete secret %s: %s", secret.id, e)

    # ------
    # Secrets
    # ------

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

        Args:
            tags: The AWS secret tags.
            created: The AWS secret creation time.
            updated: The AWS secret last updated time.
            values: The AWS secret values encoded as a JSON string (optional).

        Returns:
            The ZenML secret.

        Raises:
            KeyError: If the AWS secret is a leftover from a deleted user
                or workspace.
            ValueError: If the AWS secret is missing required tags.
        """
        # Convert the AWS secret tags to a dictionary.
        tags_dict: Dict[str, str] = {tag["Key"]: tag["Value"] for tag in tags}

        # Recover the ZenML secret metadata from the AWS secret tags.
        try:
            secret_id = UUID(tags_dict[ZENML_SECRET_ID_LABEL])
            name = tags_dict[ZENML_SECRET_NAME_LABEL]
            scope = SecretScope(tags_dict[ZENML_SECRET_SCOPE_LABEL])
            workspace_id = UUID(tags_dict[ZENML_SECRET_WORKSPACE_LABEL])
            user_id = UUID(tags_dict[ZENML_SECRET_USER_LABEL])
        except KeyError as e:
            raise ValueError(f"Invalid AWS secret: missing required tag {e}")

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
                f"Secret with ID {secret_id} is associated with a "
                f"non-existent user or workspace. Silently ignoring the "
                f"secret: {e}"
            )
            raise KeyError(f"Secret with ID {secret_id} not found")

        secret_model = SecretResponseModel(
            id=secret_id,
            name=name,
            scope=scope,
            workspace=workspace,
            user=user,
            values=json.loads(values) if values else {},
            created=created,
            updated=updated,
        )

        return secret_model

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

    @track(AnalyticsEvent.CREATED_SECRET)
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

        # The AWS Secrets Manager does not immediately reflect the newly
        # created secret in the `list_secrets` API. It is important that we
        # wait for the secret to be available in the `list_secrets` API
        # before returning the newly created secret, otherwise the secret
        # will not be visible to the user. We also rely on `list_secrets`
        # to enforce the scope rules, but given that the ZenML server runs
        # requests in separate threads, it is not entirely possible to
        # guarantee them.

        # We wait for the secret to be available in the `list_secrets` API.
        for _ in range(self.config.secret_list_refresh_timeout):
            logger.debug(f"Waiting for secret {aws_secret_id} to be listed...")
            secret_exists = False
            try:
                secrets = self.client.list_secrets(
                    Filters=[{"Key": "name", "Values": [aws_secret_id]}]
                )
                secret_exists = len(secrets["SecretList"]) > 0
            except ClientError as e:
                logger.warning(
                    f"Error checking newly created secret {aws_secret_id}: "
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
            if self.config.secret_list_refresh_timeout:
                logger.warning(
                    f"Newly created secret {aws_secret_id} not listed after "
                    f"{self.config.secret_list_refresh_timeout} seconds. "
                )

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
            logger.error(f"Error listing secrets: {e}")

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

        return Page(
            total=total,
            total_pages=total_pages,
            items=sorted_results[
                (secret_filter_model.page - 1)
                * secret_filter_model.size : secret_filter_model.page
                * secret_filter_model.size
            ],
            page=secret_filter_model.page,
            size=secret_filter_model.size,
        )

    @track(AnalyticsEvent.UPDATED_SECRET)
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

        # We wait for the secret update to be reflected in the `list_secrets`
        # API.
        for _ in range(self.config.secret_list_refresh_timeout):
            logger.debug(
                f"Waiting for secret {aws_secret_id} to be updated..."
            )
            secret_exists = False
            try:
                secrets = self.client.list_secrets(
                    Filters=[{"Key": "name", "Values": [aws_secret_id]}]
                )
                if len(secrets["SecretList"]) > 0:
                    listed_secret = secrets["SecretList"][0]
                    # The new tags must exactly match those reported in the
                    # `list_secrets` response.
                    secret_exists = all(
                        tag in listed_secret["Tags"] for tag in tags
                    )
            except ClientError as e:
                logger.warning(
                    f"Error checking updated created secret {aws_secret_id}: "
                    f"{e}. Retrying..."
                )

            if not secret_exists:
                logger.debug(
                    f"Secret {aws_secret_id} not yet updated. Retrying..."
                )
                time.sleep(1)
            else:
                logger.debug(f"Secret {aws_secret_id} updated.")
                break
        else:
            if self.config.secret_list_refresh_timeout:
                logger.warning(
                    f"Updated secret {aws_secret_id} not listed after "
                    f"{self.config.secret_list_refresh_timeout} seconds."
                )

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

    @track(AnalyticsEvent.DELETED_SECRET)
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
