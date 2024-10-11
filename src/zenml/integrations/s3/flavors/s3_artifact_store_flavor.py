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
"""Amazon S3 artifact store flavor."""

import re
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Set,
    Type,
)

from pydantic import field_validator

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.stack.authentication_mixin import AuthenticationConfigMixin
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.s3.artifact_stores import S3ArtifactStore


class S3ArtifactStoreConfig(
    BaseArtifactStoreConfig, AuthenticationConfigMixin
):
    """Configuration for the S3 Artifact Store.

    All attributes of this class except `path` will be passed to the
    `s3fs.S3FileSystem` initialization. See
    [here](https://s3fs.readthedocs.io/en/latest/) for more information on how
    to use those configuration options to connect to any S3-compatible storage.

    When you want to register an S3ArtifactStore from the CLI and need to pass
    `client_kwargs`, `config_kwargs` or `s3_additional_kwargs`, you should pass
    them as a json string:
    ```
    zenml artifact-store register my_s3_store --flavor=s3 \
    --path=s3://my_bucket --client_kwargs='\{\"endpoint_url\": \"http://my-s3-endpoint\"\}'
    ```
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}

    key: Optional[str] = SecretField(default=None)
    secret: Optional[str] = SecretField(default=None)
    token: Optional[str] = SecretField(default=None)
    client_kwargs: Optional[Dict[str, Any]] = None
    config_kwargs: Optional[Dict[str, Any]] = None
    s3_additional_kwargs: Optional[Dict[str, Any]] = None

    @field_validator("client_kwargs")
    @classmethod
    def _validate_client_kwargs(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validates the `client_kwargs` attribute.

        Args:
            value: The value to validate.

        Raises:
            ValueError: If the value is not a valid URL.

        Returns:
            The validated value.
        """
        if value is None:
            return value

        if "endpoint_url" in value and value["endpoint_url"]:
            url = value["endpoint_url"].rstrip("/")
            scheme = re.search("^([a-z0-9]+://)", url)
            if scheme is None or scheme.group() not in ("https://", "http://"):
                raise ValueError(
                    "Invalid URL for endpoint url: {url}. Should be in the form "
                    "https://hostname[:port] or http://hostname[:port]."
                )

            # When running inside a container, if the URL uses localhost, the
            # target service will not be available. We try to replace localhost
            # with one of the special Docker or K3D internal hostnames.
            value["endpoint_url"] = replace_localhost_with_internal_hostname(
                url
            )
        return value


class S3ArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Flavor of the S3 artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return S3_ARTIFACT_STORE_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type="s3-bucket",
            resource_id_attr="path",
        )

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/aws.png"

    @property
    def config_class(self) -> Type[S3ArtifactStoreConfig]:
        """The config class of the flavor.

        Returns:
            The config class of the flavor.
        """
        return S3ArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["S3ArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        from zenml.integrations.s3.artifact_stores import S3ArtifactStore

        return S3ArtifactStore
