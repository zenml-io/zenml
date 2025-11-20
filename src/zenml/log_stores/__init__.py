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
"""Implements the log stores for ZenML."""

# Base log store
# Artifact log store
from zenml.log_stores.artifact.artifact_log_store import (
    ArtifactLogStore,
)
from zenml.log_stores.artifact.artifact_log_store_flavor import (
    ArtifactLogStoreConfig,
    ArtifactLogStoreFlavor,
)
from zenml.log_stores.base_log_store import (
    BaseLogStore,
    BaseLogStoreConfig,
    BaseLogStoreFlavor,
)
from zenml.log_stores.datadog.datadog_flavor import (
    DatadogLogStoreConfig,
    DatadogLogStoreFlavor,
)

# Datadog log store
from zenml.log_stores.datadog.datadog_log_store import (
    DatadogLogStore,
)
from zenml.log_stores.otel.otel_flavor import (
    OtelLogStoreConfig,
    OtelLogStoreFlavor,
)

# OpenTelemetry log store
from zenml.log_stores.otel.otel_log_store import OtelLogStore

# Logging utilities
from zenml.log_stores.utils import (
    LogEntry,
    LoggingContext,
    fetch_logs,
    generate_logs_request,
    is_logging_enabled,
    search_logs_by_source,
    setup_orchestrator_logging,
)

__all__ = [
    "ArtifactLogStore",
    "ArtifactLogStoreConfig",
    "ArtifactLogStoreFlavor",
    "BaseLogStore",
    "BaseLogStoreConfig",
    "BaseLogStoreFlavor",
    "DatadogLogStore",
    "DatadogLogStoreConfig",
    "DatadogLogStoreFlavor",
    "LogEntry",
    "LoggingContext",
    "OtelLogStore",
    "OtelLogStoreConfig",
    "OtelLogStoreFlavor",
    "fetch_logs",
    "generate_logs_request",
    "is_logging_enabled",
    "search_logs_by_source",
    "setup_orchestrator_logging",
]
