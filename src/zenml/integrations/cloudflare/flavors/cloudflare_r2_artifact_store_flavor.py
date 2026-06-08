#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Cloudflare R2 artifact store flavor."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Set,
    Type,
)

from pydantic import Field, model_validator

from zenml.artifact_stores import BaseArtifactStoreFlavor
from zenml.integrations.cloudflare import (
    CLOUDFLARE_R2_ARTIFACT_STORE_FLAVOR,
)
from zenml.integrations.cloudflare.utils import split_r2_path
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)

if TYPE_CHECKING:
    from zenml.integrations.cloudflare.artifact_stores import R2ArtifactStore


class R2ArtifactStoreConfig(S3ArtifactStoreConfig):
    """Configuration for the Cloudflare R2 Artifact Store.

    R2 is S3-compatible, so this reuses the S3 artifact store configuration and
    filesystem. The only R2-specific requirement is the S3 API endpoint, which
    is derived from the Cloudflare account ID unless an explicit `endpoint_url`
    is provided via `client_kwargs`.
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"r2://"}

    account_id: Optional[str] = Field(
        default=None,
        description="Cloudflare account ID used to construct the R2 "
        "S3-compatible endpoint "
        "'https://<account_id>.r2.cloudflarestorage.com'. Required unless an "
        "explicit 'endpoint_url' is supplied in 'client_kwargs'. Example: "
        "'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'",
    )

    @model_validator(mode="before")
    @classmethod
    def _configure_r2_endpoint(cls, data: Any) -> Any:
        """Derives R2-specific client/config defaults from the account ID.

        Runs before validation because the config is frozen once constructed.

        Args:
            data: The raw input data for the config.

        Returns:
            The input data with the R2 endpoint and signing region set.

        Raises:
            ValueError: If neither `account_id` nor an explicit `endpoint_url`
                is provided.
        """
        if not isinstance(data, dict):
            return data

        client_kwargs: Dict[str, Any] = dict(data.get("client_kwargs") or {})
        if not client_kwargs.get("endpoint_url"):
            account_id = data.get("account_id")
            if not account_id:
                raise ValueError(
                    "The Cloudflare R2 artifact store requires either an "
                    "`account_id` or an explicit `endpoint_url` in "
                    "`client_kwargs` to locate the R2 S3 API endpoint."
                )
            client_kwargs["endpoint_url"] = (
                f"https://{account_id}.r2.cloudflarestorage.com"
            )
        data["client_kwargs"] = client_kwargs

        # R2 ignores the AWS region, but botocore's SigV4 signer still requires
        # one. Cloudflare documents "auto" for S3-compatible clients.
        config_kwargs: Dict[str, Any] = dict(data.get("config_kwargs") or {})
        config_kwargs.setdefault("region_name", "auto")
        data["config_kwargs"] = config_kwargs
        return data

    @property
    def bucket(self) -> str:
        """The R2 bucket name parsed from the artifact store path.

        Returns:
            The bucket name of the artifact store.
        """
        if self._bucket is None:
            self._bucket, _ = split_r2_path(self.path)
        return self._bucket


class R2ArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Flavor of the Cloudflare R2 artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return CLOUDFLARE_R2_ARTIFACT_STORE_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Cloudflare R2"

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/cloudflare.png"

    @property
    def config_class(self) -> Type[R2ArtifactStoreConfig]:
        """The config class of the flavor.

        Returns:
            The config class of the flavor.
        """
        return R2ArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["R2ArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        from zenml.integrations.cloudflare.artifact_stores import (
            R2ArtifactStore,
        )

        return R2ArtifactStore
