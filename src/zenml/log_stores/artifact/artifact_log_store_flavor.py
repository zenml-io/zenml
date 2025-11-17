#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Artifact log store flavor implementation."""

from typing import TYPE_CHECKING, Type

from zenml.log_stores.otel.otel_flavor import (
    OtelLogStoreConfig,
    OtelLogStoreFlavor,
)

if TYPE_CHECKING:
    from zenml.log_stores.base_log_store import BaseLogStore


class ArtifactLogStoreConfig(OtelLogStoreConfig):
    """Configuration for the artifact log store.

    This log store saves logs to the artifact store using OTEL infrastructure.
    """


class ArtifactLogStoreFlavor(OtelLogStoreFlavor):
    """Artifact log store flavor implementation."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "artifact"

    @property
    def docs_url(self) -> str:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return "https://docs.zenml.io/stack-components/log-stores/artifact"

    @property
    def logo_url(self) -> str:
        """URL to the flavor logo.

        Returns:
            The URL to the flavor logo.
        """
        # TODO: Add a logo for the artifact log store
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/log_store/artifact.png"

    @property
    def config_class(self) -> Type[ArtifactLogStoreConfig]:
        """Returns `ArtifactLogStoreConfig` config class.

        Returns:
            The config class.
        """
        return ArtifactLogStoreConfig

    @property
    def implementation_class(self) -> Type["BaseLogStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.artifact.artifact_log_store import (
            ArtifactLogStore,
        )

        return ArtifactLogStore
