#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import logging
from enum import Enum

from zenml.utils.enum_utils import StrEnum


class ExecutionStatus(StrEnum):
    """Enum that represents the current status of a step or pipeline run."""

    FAILED = "failed"
    COMPLETED = "completed"
    RUNNING = "running"
    CACHED = "cached"


class LoggingLevels(Enum):
    """Enum for logging levels."""

    NOTSET = logging.NOTSET
    ERROR = logging.ERROR
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL


class StackComponentFlavor(StrEnum):
    """Abstract base class for all stack component flavors."""


class ArtifactStoreFlavor(StackComponentFlavor):
    """All supported artifact store flavors."""

    LOCAL = "local"
    GCP = "gcp"
    S3 = "s3"


class MetadataStoreFlavor(StackComponentFlavor):
    """All supported metadata store flavors."""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    KUBEFLOW = "kubeflow"


class ContainerRegistryFlavor(StackComponentFlavor):
    """All supported container registry flavors."""

    DEFAULT = "default"


class OrchestratorFlavor(StackComponentFlavor):
    """All supported orchestrator flavors."""

    LOCAL = "local"
    KUBEFLOW = "kubeflow"
    AIRFLOW = "airflow"


class StackComponentType(StrEnum):
    """All possible types a `StackComponent` can have."""

    ORCHESTRATOR = "orchestrator"
    METADATA_STORE = "metadata_store"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"

    @property
    def plural(self) -> str:
        """Returns the plural of the enum value."""
        if self == StackComponentType.CONTAINER_REGISTRY:
            return "container_registries"

        return f"{self.value}s"
