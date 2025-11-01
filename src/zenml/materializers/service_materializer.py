#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of a materializer to read and write ZenML service instances."""

import os
import uuid
from typing import TYPE_CHECKING, Any, ClassVar

from zenml.client import Client
from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.services.service import BaseDeploymentService, BaseService

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

SERVICE_CONFIG_FILENAME = "service.json"


class ServiceMaterializer(BaseMaterializer):
    """Materializer to read/write service instances."""

    ASSOCIATED_TYPES: ClassVar[tuple[type[Any], ...]] = (BaseService,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.SERVICE

    def load(self, data_type: type[Any]) -> BaseService:
        """Creates and returns a service.

        This service is instantiated from the serialized service configuration
        and last known status information saved as artifact.

        Args:
            data_type: The type of the data to read.

        Returns:
            A ZenML service instance.
        """
        filepath = os.path.join(self.uri, SERVICE_CONFIG_FILENAME)
        with self.artifact_store.open(filepath, "r") as f:
            service_id = f.read().strip()

        service = Client().get_service(name_id_or_prefix=uuid.UUID(service_id))
        return BaseDeploymentService.from_model(service)

    def save(self, service: BaseService) -> None:
        """Writes a ZenML service.

        The configuration and last known status of the input service instance
        are serialized and saved as an artifact.

        Args:
            service: A ZenML service instance.
        """
        filepath = os.path.join(self.uri, SERVICE_CONFIG_FILENAME)
        with self.artifact_store.open(filepath, "w") as f:
            f.write(str(service.uuid))

    def extract_metadata(
        self, service: BaseService
    ) -> dict[str, "MetadataType"]:
        """Extract metadata from the given service.

        Args:
            service: The service to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        from zenml.metadata.metadata_types import Uri

        if prediction_url := service.get_prediction_url() or None:
            return {"uri": Uri(prediction_url)}
        return {}
