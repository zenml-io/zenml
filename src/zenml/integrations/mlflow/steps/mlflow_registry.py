#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the MLflow model registration pipeline step."""

from typing import Any, Optional, cast

from zenml import __version__, step
from zenml.client import Client
from zenml.environment import Environment
from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    StepEnvironment,
)

logger = get_logger(__name__)


@step(enable_cache=True)
def mlflow_register_model_step(
    model: Any,
    name: str,
    version: Optional[str] = None,
    model_name: str = "model",
    model_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    run_name: Optional[str] = None,
    run_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[ModelRegistryModelMetadata] = None,
) -> None:
    """MLflow model registry step.

    Searches or logs a model to MLflow and registers it in the MLflow model
    registry with the following precedence order:
    1. If `model_uri` is set, register this file directly.
    2. Else, check if the model was already logged to MLflow and register that.
    3. If no model was found, start a new MLflow run, log the model, and
        register it.

    Args:
        model: Model to be registered.
        name: Name of the new model in the model registry.
        version: Version of the new model in the model registry.
        model_name: Name of the model artifact to search or log.
        model_uri: MLflow URI of the model. If provided, register the model
            from this URI instead of searching the model artifact in MLflow.
        experiment_name: Name of the MLflow experiment in which to search or
            log the model.
        run_name: Name of the MLflow run in which to search or log the model.
        run_id: ID of the MLflow run in which to search the model. Overrides
            `experiment_name` and `run_name` if provided.
        description: Description of the model for the model registry.
        metadata: Metadata of the model version for the model registry.

    Raises:
        ValueError: If the model registry is not an MLflow model registry.
    """
    # fetch the MLflow model registry
    model_registry = Client().active_stack.model_registry
    if not isinstance(model_registry, MLFlowModelRegistry):
        raise ValueError(
            "The MLflow model registry step can only be used with an "
            "MLflow model registry."
        )

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    experiment_name = experiment_name or pipeline_name
    run_name = run_name or step_env.run_name
    pipeline_run_uuid = str(step_env.step_run_info.run_id)
    zenml_workspace = str(model_registry.workspace)

    # If no run ID was set, try to get it from the model registry
    if not model_uri:
        assert model_name is not None
        model_uri = model_registry.find_or_log_mlflow_model(
            model=model,
            model_name=model_name,
            experiment_name=experiment_name,
            run_name=run_name,
            run_id=run_id,
        )

    # Check metadata
    if not metadata:
        metadata = ModelRegistryModelMetadata()
    if metadata.zenml_version is None:
        metadata.zenml_version = __version__
    if metadata.zenml_pipeline_name is None:
        metadata.zenml_pipeline_name = pipeline_name
    if metadata.zenml_run_name is None:
        metadata.zenml_run_name = run_name
    if metadata.zenml_pipeline_run_uuid is None:
        metadata.zenml_pipeline_run_uuid = pipeline_run_uuid
    if metadata.zenml_workspace is None:
        metadata.zenml_workspace = zenml_workspace

    # Register model version
    model_version = model_registry.register_model_version(
        name=name,
        version=version or "1",
        model_source_uri=model_uri,
        description=description,
        metadata=metadata,
    )

    logger.info(
        f"Registered model {name} "
        f"with version {model_version.version} "
        f"from source {model_uri}."
    )
