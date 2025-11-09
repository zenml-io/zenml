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
"""Sync step for MLflow-Notion model registry integration."""

from typing import Annotated, Dict, Optional

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow_notion.model_registries import (
    MLFlowNotionModelRegistry,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def mlflow_notion_sync_step(
    model_name: Optional[str] = None,
    cleanup_orphans: bool = False,
) -> Annotated[Dict[str, int], "sync_stats"]:
    """Sync MLflow registry state to Notion.

    Only syncs models tagged with zenml.mlflow_notion_managed.

    Args:
        model_name: Sync specific model only, or all managed models if None.
        cleanup_orphans: Archive Notion entries not found in MLflow.

    Returns:
        Statistics dictionary with keys: created, updated, unchanged,
        orphaned, errors.

    Raises:
        RuntimeError: If the active model registry is not mlflow_notion flavor.
    """
    client = Client()
    model_registry = client.active_stack.model_registry

    if not model_registry:
        raise RuntimeError(
            "No model registry found in active stack. Please register a "
            "mlflow_notion model registry to your stack."
        )

    if not isinstance(model_registry, MLFlowNotionModelRegistry):
        raise RuntimeError(
            f"Active model registry is '{model_registry.flavor}' but this step "
            f"requires 'mlflow_notion' flavor. Please set a stack with "
            f"mlflow_notion model registry."
        )

    logger.info(
        f"Starting MLflow→Notion sync"
        f"{f' for model: {model_name}' if model_name else ' for all managed models'}"
    )

    stats = model_registry.sync_to_notion(
        model_name=model_name,
        cleanup_orphans=cleanup_orphans,
    )

    logger.info(
        f"Sync completed: {stats['created']} created, {stats['updated']} updated, "
        f"{stats['unchanged']} unchanged, {stats['errors']} errors"
    )

    if cleanup_orphans:
        logger.info(f"Cleaned up {stats['orphaned']} orphaned entries")

    return stats
