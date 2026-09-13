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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Unit tests for the MLflow model registry."""

from unittest.mock import MagicMock, patch

from mlflow.entities.model_registry import ModelVersion as MLflowModelVersion

from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)
from zenml.model_registries.base_model_registry import ModelVersionStage


def test_register_model_version_without_mlflow_stage() -> None:
    """Register an MLflow model version that does not have a legacy stage."""
    mlflow_model_version = MLflowModelVersion(
        name="catalog.schema.model",
        version="1",
        creation_timestamp=1,
        current_stage=None,
        source="models:/catalog.schema.model/1",
    )
    mlflow_client = MagicMock()
    mlflow_client.create_model_version.return_value = mlflow_model_version
    model_registry = object.__new__(MLFlowModelRegistry)
    model_registry._client = mlflow_client

    with (
        patch.object(model_registry, "get_model"),
        patch(
            "zenml.integrations.mlflow.model_registries."
            "mlflow_model_registry.get_model_info",
            side_effect=OSError,
        ),
    ):
        registered_model_version = model_registry.register_model_version(
            name="catalog.schema.model",
            model_source_uri="models:/catalog.schema.model/1",
        )

    assert registered_model_version.stage == ModelVersionStage.NONE
