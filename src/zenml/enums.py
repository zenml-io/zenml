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
from typing import Type

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


class StackComponentType(StrEnum):
    """All possible types a `StackComponent` can have."""

    ORCHESTRATOR = "orchestrator"
    METADATA_STORE = "metadata_store"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    STEP_OPERATOR = "step_operator"
    SECRETS_MANAGER = "secrets_manager"

    @property
    def plural(self) -> str:
        """Returns the plural of the enum value."""
        if self == StackComponentType.CONTAINER_REGISTRY:
            return "container_registries"

        return f"{self.value}s"


class StackComponentFlavor(StrEnum):
    """Abstract base class for all stack component flavors."""

    @staticmethod
    def for_type(
        component_type: StackComponentType,
    ) -> Type["StackComponentFlavor"]:
        """Get the corresponding flavor child-type for a component type."""
        if component_type == StackComponentType.ARTIFACT_STORE:
            return ArtifactStoreFlavor
        elif component_type == StackComponentType.METADATA_STORE:
            return MetadataStoreFlavor
        elif component_type == StackComponentType.CONTAINER_REGISTRY:
            return ContainerRegistryFlavor
        elif component_type == StackComponentType.ORCHESTRATOR:
            return OrchestratorFlavor
        elif component_type == StackComponentType.STEP_OPERATOR:
            return StepOperatorFlavor
        elif component_type == StackComponentType.SECRETS_MANAGER:
            return SecretsManagerFlavor
        else:
            raise ValueError(
                f"Unsupported Stack Component Type {component_type.value}"
            )


class ArtifactStoreFlavor(StackComponentFlavor):
    """All supported artifact store flavors."""

    AZURE = "azure"
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
    VERTEX = "vertex"


class StepOperatorFlavor(StackComponentFlavor):
    """All supported step operator flavors."""

    AZUREML = "azureml"
    SAGEMAKER = "sagemaker"
    VERTEX = "vertex"


class MetadataContextTypes(Enum):
    """All possible types that contexts can have within pipeline nodes"""

    STACK = "stack"
    PIPELINE_REQUIREMENTS = "pipeline_requirements"


class SecretsManagerFlavor(StackComponentFlavor):
    """All supported orchestrator flavors."""

    LOCAL = "local"
    LOCAL_SQLITE = "local_sqlite"
    AWS = "aws"


class SecretSchemaType(StrEnum):
    """All supported secret schema types."""

    AWS = "aws"
    ARBITRARY = "arbitrary"


class StoreType(StrEnum):
    """Repository Store Backend Types"""

    LOCAL = "local"
    SQL = "sql"
    REST = "rest"
