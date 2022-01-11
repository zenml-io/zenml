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


class ArtifactStoreTypes(str, Enum):
    """All supported Artifact Store types."""

    local = "local"
    gcp = "gcp"

    def __str__(self) -> str:
        """Returns the enum string value."""
        return self.value


class MLMetadataTypes(str, Enum):
    """All supported ML Metadata types."""

    sqlite = "sqlite"
    mysql = "mysql"
    kubeflow = "kubeflow"

    def __str__(self) -> str:
        """Returns the enum string value."""
        return self.value


class OrchestratorTypes(str, Enum):
    """All supported Orchestrator types"""

    local = "local"
    airflow = "airflow"
    kubeflow = "kubeflow"

    def __str__(self) -> str:
        """Returns the enum string value."""
        return self.value


class StackTypes(str, Enum):
    """All supported Stack types."""

    base = "base"


class ExecutionStatus(Enum):
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
