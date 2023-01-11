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
from typing import Any, Type

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.services.service import BaseService
from zenml.services.service_registry import ServiceRegistry

SERVICE_CONFIG_FILENAME = "service.json"


class ServiceMaterializer(BaseMaterializer):
    """Materializer to read/write service instances."""

    ASSOCIATED_TYPES = (BaseService,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.SERVICE

    def load(self, data_type: Type[Any]) -> BaseService:
        """Creates and returns a service.

        This service is instantiated from the serialized service configuration
        and last known status information saved as artifact.

        Args:
            data_type: The type of the data to read.

        Returns:
            A ZenML service instance.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, SERVICE_CONFIG_FILENAME)
        with fileio.open(filepath, "r") as f:
            service = ServiceRegistry().load_service_from_json(f.read())
        return service

    def save(self, service: BaseService) -> None:
        """Writes a ZenML service.

        The configuration and last known status of the input service instance
        are serialized and saved as an artifact.

        Args:
            service: A ZenML service instance.
        """
        super().save(service)
        filepath = os.path.join(self.uri, SERVICE_CONFIG_FILENAME)
        with fileio.open(filepath, "w") as f:
            f.write(service.json(indent=4))
