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
"""Implementation of the DigitalOcean Spaces Artifact Store.

DigitalOcean Spaces exposes an S3-compatible API that behaves identically to S3
for the read/write operations ZenML needs, so this class subclasses
:class:`S3ArtifactStore`. The only Spaces-specific behavior is the endpoint
URL, which is derived from the configured ``region`` at runtime rather than
persisted in the config model, so that a later region update is never shadowed
by a stale persisted endpoint.
"""

from typing import Any, Dict, cast

from zenml.integrations.digitalocean.flavors.digitalocean_artifact_store_flavor import (
    DigitalOceanSpacesArtifactStoreConfig,
)
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
)


class DigitalOceanSpacesArtifactStore(S3ArtifactStore):
    """Artifact Store backed by a DigitalOcean Spaces bucket via the S3 API."""

    @property
    def config(self) -> DigitalOceanSpacesArtifactStoreConfig:
        """Get the typed config of this artifact store.

        Returns:
            The config of this artifact store.
        """
        return cast(DigitalOceanSpacesArtifactStoreConfig, self._config)

    def _apply_spaces_endpoint(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Inject the region-derived Spaces endpoint unless one is set.

        An explicit ``endpoint_url`` (from ``client_kwargs``) always takes
        precedence over the region-derived one.

        Args:
            kwargs: Client kwargs to extend, mutated in place.

        Returns:
            The same kwargs, with the Spaces ``endpoint_url`` filled in from
            the configured ``region`` if it was not set explicitly.
        """
        if not kwargs.get("endpoint_url") and self.config.region:
            kwargs["endpoint_url"] = (
                f"https://{self.config.region}.digitaloceanspaces.com"
            )
        return kwargs

    def _build_filesystem_kwargs(self) -> Dict[str, Any]:
        """Build the s3fs constructor kwargs with the Spaces endpoint.

        Returns:
            Keyword arguments for the S3-compatible filesystem.
        """
        kwargs = super()._build_filesystem_kwargs()
        self._apply_spaces_endpoint(kwargs["client_kwargs"])
        return kwargs

    def _build_boto3_kwargs(self) -> Dict[str, Any]:
        """Build Spaces-aware kwargs for the boto3.resource path.

        The parent applies ``client_kwargs`` and credentials; this override
        mirrors the Spaces endpoint and the ``config_kwargs`` (as a botocore
        ``Config``) onto the ``boto3.resource('s3', ...)`` path so both code
        paths address the same endpoint with the same client configuration.

        Returns:
            kwargs for ``boto3.resource('s3', ...)``.
        """
        kwargs = self._apply_spaces_endpoint(super()._build_boto3_kwargs())
        if self.config.config_kwargs and "config" not in kwargs:
            from botocore.config import Config

            kwargs["config"] = Config(**self.config.config_kwargs)
        return kwargs
