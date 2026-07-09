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
:class:`S3ArtifactStore`. The only Spaces-specific behaviour is the endpoint
URL, which is derived from the configured ``region`` at runtime rather than
persisted in the config model.
"""

from typing import Any, Dict, Optional, cast

from zenml.integrations.digitalocean.flavors.digitalocean_artifact_store_flavor import (
    DigitalOceanSpacesArtifactStoreConfig,
    spaces_endpoint_url,
)
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
    ZenMLS3Filesystem,
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

    def _with_spaces_endpoint(
        self, client_kwargs: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build client kwargs with the region-derived Spaces endpoint.

        An explicit ``endpoint_url`` in ``client_kwargs`` always takes
        precedence over the region-derived one.

        Args:
            client_kwargs: The client kwargs from the config, if any.

        Returns:
            Client kwargs including the Spaces ``endpoint_url``.
        """
        kwargs = dict(client_kwargs) if client_kwargs else {}
        if not kwargs.get("endpoint_url") and self.config.region:
            kwargs["endpoint_url"] = spaces_endpoint_url(self.config.region)
        return kwargs

    @property
    def filesystem(self) -> ZenMLS3Filesystem:
        """The Spaces S3-compatible filesystem for this artifact store.

        Returns:
            The filesystem object.
        """
        if self._filesystem and not self.connector_has_expired():
            return self._filesystem

        key, secret, token, region = self.get_credentials()
        self._filesystem = ZenMLS3Filesystem(
            key=key,
            secret=secret,
            token=token,
            client_kwargs=self._with_spaces_endpoint(
                self.config.client_kwargs
            ),
            config_kwargs=self.config.config_kwargs,
            s3_additional_kwargs=self.config.s3_additional_kwargs,
        )
        return self._filesystem

    def _build_boto3_kwargs(self) -> Dict[str, Any]:
        """Build Spaces-aware kwargs for the boto3.resource path.

        The parent applies ``config_kwargs`` to the s3fs filesystem; this
        override mirrors the Spaces endpoint on the ``boto3.resource('s3', ...)``
        path so both code paths address the same endpoint.

        Returns:
            kwargs for ``boto3.resource('s3', ...)``.
        """
        kwargs = super()._build_boto3_kwargs()
        if not kwargs.get("endpoint_url") and self.config.region:
            kwargs["endpoint_url"] = spaces_endpoint_url(self.config.region)
        return kwargs
