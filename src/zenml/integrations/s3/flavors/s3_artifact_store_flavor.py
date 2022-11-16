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

import json
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Set,
    Type,
    Union,
)

from pydantic import validator

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.s3.artifact_stores import S3ArtifactStore


class S3ArtifactStoreConfig(BaseArtifactStoreConfig, AuthenticationConfigMixin):
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
    --path=s3://my_bucket --client_kwargs='{"endpoint_url": "http://my-s3-endpoint"}'
    ```
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}

    key: Optional[str] = SecretField()
    secret: Optional[str] = SecretField()
    token: Optional[str] = SecretField()
    client_kwargs: Optional[Dict[str, Any]] = None
    config_kwargs: Optional[Dict[str, Any]] = None
    s3_additional_kwargs: Optional[Dict[str, Any]] = None

    @validator(
        "client_kwargs", "config_kwargs", "s3_additional_kwargs", pre=True
    )
    def _convert_json_string(
        cls, value: Union[None, str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Converts potential JSON strings passed via the CLI to dictionaries.

        Args:
            value: The value to convert.

        Returns:
            The converted value.

        Raises:
            TypeError: If the value is not a `str`, `Dict` or `None`.
            ValueError: If the value is an invalid json string or a json string
                that does not decode into a dictionary.
        """
        if isinstance(value, str):
            try:
                dict_ = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid json string '{value}'") from e

            if not isinstance(dict_, Dict):
                raise ValueError(
                    f"Json string '{value}' did not decode into a dictionary."
                )

            return dict_
        elif isinstance(value, Dict) or value is None:
            return value
        else:
            raise TypeError(f"{value} is not a json string or a dictionary.")


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
