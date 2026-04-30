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
operations ZenML needs, so this class is a thin subclass of
:class:`S3ArtifactStore`. All filesystem behavior (copy, glob, walk,
versioning shielding, etc.) is inherited unchanged.

This subclass provides two narrow overrides on top of the parent:

- A typed ``config`` property returning :class:`B2ArtifactStoreConfig`
  so callers get the B2-specific config type.
- ``_build_boto3_kwargs`` is overridden to forward the config's
  ``config_kwargs`` (notably ``user_agent_extra``) into the
  ``boto3.resource('s3', ...)`` code path. The parent only applies
  ``config_kwargs`` to the s3fs filesystem, so without this override the
  boto3 path would silently miss the same client configuration.
"""

from typing import Any, Dict, cast

from zenml.integrations.b2.flavors.b2_artifact_store_flavor import (
    B2ArtifactStoreConfig,
)
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
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

    def _build_boto3_kwargs(self) -> Dict[str, Any]:
        """Forward ``config_kwargs`` into the boto3.resource path.

        The parent only applies ``config_kwargs`` to the s3fs filesystem;
        this override mirrors that on the ``boto3.resource('s3', ...)``
        path so both code paths see the same client configuration.

        Returns:
            kwargs for ``boto3.resource('s3', ...)``.
        """
        kwargs = super()._build_boto3_kwargs()
        if self.config.config_kwargs and "config" not in kwargs:
            from botocore.config import Config

            kwargs["config"] = Config(**self.config.config_kwargs)
        return kwargs
