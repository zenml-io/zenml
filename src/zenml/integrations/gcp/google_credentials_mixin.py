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
"""Implementation of the Google credentials mixin."""

from typing import TYPE_CHECKING, Optional, Tuple, cast

from zenml.logger import get_logger
from zenml.stack.stack_component import StackComponent, StackComponentConfig

if TYPE_CHECKING:
    from google.auth.credentials import Credentials


logger = get_logger(__name__)


class GoogleCredentialsConfigMixin(StackComponentConfig):
    """Config mixin for Google Cloud Platform credentials.

    Attributes:
        project: GCP project name. If `None`, the project will be inferred from
            the environment.
        service_account_path: path to the service account credentials file to be
            used for authentication. If not provided, the default credentials
            will be used.
    """

    project: Optional[str] = None
    service_account_path: Optional[str] = None


class GoogleCredentialsMixin(StackComponent):
    """StackComponent mixin to get Google Cloud Platform credentials."""

    @property
    def config(self) -> GoogleCredentialsConfigMixin:
        """Returns the `GoogleCredentialsConfigMixin` config.

        Returns:
            The configuration.
        """
        return cast(GoogleCredentialsConfigMixin, self._config)

    def _get_authentication(self) -> Tuple["Credentials", str]:
        """Get GCP credentials and the project ID associated with the credentials.

        If `service_account_path` is provided, then the credentials will be
        loaded from the file at that path. Otherwise, the default credentials
        will be used.

        Returns:
            A tuple containing the credentials and the project ID associated to
            the credentials.

        Raises:
            RuntimeError: If the linked connector returns an unexpected type of
                credentials.
        """
        from google.auth import default, load_credentials_from_file
        from google.auth.credentials import Credentials

        from zenml.integrations.gcp.service_connectors import (
            GCPServiceConnector,
        )

        connector = self.get_connector()
        if connector:
            credentials = connector.connect()
            if not isinstance(credentials, Credentials) or not isinstance(
                connector, GCPServiceConnector
            ):
                raise RuntimeError(
                    f"Expected google.auth.credentials.Credentials while "
                    "trying to use the linked connector, but got "
                    f"{type(credentials)}."
                )
            return credentials, connector.config.gcp_project_id

        if self.config.service_account_path:
            credentials, project_id = load_credentials_from_file(
                self.config.service_account_path
            )
        else:
            credentials, project_id = default()

        if self.config.project and self.config.project != project_id:
            logger.warning(
                "Authenticated with project `%s`, but this %s is "
                "configured to use the project `%s`.",
                project_id,
                self.type,
                self.config.project,
            )

        # If the project was set in the configuration, use it. Otherwise, use
        # the project that was used to authenticate.
        project_id = self.config.project if self.config.project else project_id
        return credentials, project_id
