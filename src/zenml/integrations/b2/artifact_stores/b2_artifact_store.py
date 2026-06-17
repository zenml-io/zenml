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
"""Implementation of the Backblaze B2 Artifact Store.

B2's S3-compatible API behaves identically to S3 for the read/write
operations ZenML needs, so this class subclasses :class:`S3ArtifactStore`.
The B2-specific runtime fallbacks are applied here instead of in the config
model so environment-derived values are not persisted during component
registration.
"""

import os
from typing import Any, Dict, Optional, Tuple, cast

from zenml.integrations.b2.flavors.b2_artifact_store_flavor import (
    B2_APPLICATION_KEY_ENV_VAR,
    B2_KEY_ID_ENV_VAR,
    B2_USER_AGENT,
    DEFAULT_B2_ENDPOINT_URL,
    B2ArtifactStoreConfig,
)
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
    ZenMLS3Filesystem,
)


class B2ArtifactStore(S3ArtifactStore):
    """Artifact Store backed by a Backblaze B2 bucket via the S3 API."""

    @property
    def config(self) -> B2ArtifactStoreConfig:
        """Get the typed config of this artifact store.

        Returns:
            The config of this artifact store.
        """
        return cast(B2ArtifactStoreConfig, self._config)

    def get_credentials(
        self,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Gets authentication credentials for the B2 filesystem.

        Returns:
            Tuple (key, secret, token, region) of credentials used to
            authenticate with the S3-compatible B2 filesystem.
        """
        key, secret, token, region = super().get_credentials()

        if key is None:
            key = os.environ.get(B2_KEY_ID_ENV_VAR)
        if secret is None:
            secret = os.environ.get(B2_APPLICATION_KEY_ENV_VAR)

        return key, secret, token, region

    @staticmethod
    def _with_b2_user_agent(
        config_kwargs: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build botocore config kwargs with the B2 user agent suffix."""
        kwargs = config_kwargs.copy() if config_kwargs else {}
        existing_ua = (kwargs.get("user_agent_extra") or "").strip()
        if B2_USER_AGENT not in existing_ua:
            kwargs["user_agent_extra"] = (
                f"{existing_ua} {B2_USER_AGENT}".strip()
            )
        return kwargs

    @staticmethod
    def _with_b2_endpoint(
        client_kwargs: Optional[Dict[str, Any]],
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build client kwargs with the B2 endpoint fallback."""
        kwargs: Dict[str, Any] = {}
        if region:
            kwargs["region_name"] = region
        if client_kwargs:
            kwargs.update(client_kwargs)
        if not kwargs.get("endpoint_url"):
            kwargs["endpoint_url"] = DEFAULT_B2_ENDPOINT_URL
        return kwargs

    @property
    def filesystem(self) -> ZenMLS3Filesystem:
        """The B2 S3-compatible filesystem for this artifact store.

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
            client_kwargs=self._with_b2_endpoint(
                self.config.client_kwargs,
                region=region,
            ),
            config_kwargs=self._with_b2_user_agent(self.config.config_kwargs),
            s3_additional_kwargs=self.config.s3_additional_kwargs,
        )
        return self._filesystem

    def _build_boto3_kwargs(self) -> Dict[str, Any]:
        """Build B2-aware kwargs for the boto3.resource path.

        The parent only applies ``config_kwargs`` to the s3fs filesystem; this
        override mirrors that on the ``boto3.resource('s3', ...)`` path so both
        code paths see the same client configuration.

        Returns:
            kwargs for ``boto3.resource('s3', ...)``.
        """
        kwargs = super()._build_boto3_kwargs()
        if not kwargs.get("endpoint_url"):
            kwargs["endpoint_url"] = DEFAULT_B2_ENDPOINT_URL
        if "config" not in kwargs:
            from botocore.config import Config

            kwargs["config"] = Config(
                **self._with_b2_user_agent(self.config.config_kwargs)
            )
        return kwargs
