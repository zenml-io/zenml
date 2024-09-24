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

from typing import Optional

from mlflow.tracking import artifact_utils

from zenml import __version__, get_step_context, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)

logger = get_logger(__name__)


@step(enable_cache=True)
def mlflow_register_model_step(
    model: UnmaterializedArtifact,
    name: str,
    version: Optional[str] = None,
    trained_model_name: Optional[str] = "model",
    model_source_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    run_name: Optional[str] = None,
    run_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[ModelRegistryModelMetadata] = None,
) -> None:
    """MLflow model registry step.

    Args:
        model: Model to be registered, This is not used in the step, but is
            required to trigger the step when the model is trained.
        name: The name of the model.
        version: The version of the model.
        trained_model_name: Name of the model artifact in MLflow.
        model_source_uri: The path to the model. If not provided, the model will
            be fetched from the MLflow tracking server via the
            `trained_model_name`.
        experiment_name: Name of the experiment to be used for the run.
        run_name: Name of the run to be created.
        run_id: ID of the run to be used.
        description: A description of the model version.
        metadata: A list of metadata to associate with the model version

    Raises:
        ValueError: If the model registry is not an MLflow model registry.
        ValueError: If the experiment tracker is not an MLflow experiment tracker.
        RuntimeError: If no model source URI is provided and no model is found.
        RuntimeError: If no run ID is provided and no run is found.
    """
    # get the experiment tracker and check if it is an MLflow experiment tracker.
    experiment_tracker = Client().active_stack.experiment_tracker
    if not isinstance(experiment_tracker, MLFlowExperimentTracker):
        raise ValueError(
            "The MLflow model registry step can only be used with an "
            "MLflow experiment tracker. Please add an MLflow experiment "
            "tracker to your stack."
        )

    # fetch the MLflow model registry
    model_registry = Client().active_stack.model_registry
    if not isinstance(model_registry, MLFlowModelRegistry):
        raise ValueError(
            "The MLflow model registry step can only be used with an "
            "MLflow model registry."
        )

    # get pipeline name, step name and run id
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    current_run_name = step_context.pipeline_run.name
    pipeline_run_uuid = str(step_context.pipeline_run.id)
    zenml_workspace = str(model_registry.workspace)

    # Get MLflow run ID either from params or from experiment tracker using
    # pipeline name and run name
    mlflow_run_id = run_id or experiment_tracker.get_run_id(
        experiment_name=experiment_name or pipeline_name,
        run_name=run_name or current_run_name,
    )
    # If no value was set at all, raise an error
    if not mlflow_run_id:
        raise RuntimeError(
            f"Could not find MLflow run for experiment {pipeline_name} "
            f"and run {run_name}."
        )

    # Get MLflow client
    client = model_registry.mlflow_client
    # Lastly, check if the run ID is valid
    try:
        client.get_run(run_id=mlflow_run_id).info.run_id
    except Exception:
        raise RuntimeError(
            f"Could not find MLflow run with ID {mlflow_run_id}."
        )

    # Set model source URI
    model_source_uri = model_source_uri or None

    # Check if the run ID have a model artifact if no model source URI is set.
    if not model_source_uri and client.list_artifacts(
        mlflow_run_id, trained_model_name
    ):
        model_source_uri = artifact_utils.get_artifact_uri(
            run_id=mlflow_run_id, artifact_path=trained_model_name
        )
    if not model_source_uri:
        raise RuntimeError(
            "No model source URI provided or no model found in the "
            "MLflow tracking server for the given inputs."
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

    # Check the model extra
    if metadata.model_extra is None:
        metadata.__pydantic_extra__ = {"mlflow_run_id": mlflow_run_id}
    elif metadata.model_extra.get("mlflow_run_id", None) is None:
        metadata.model_extra["mlflow_run_id"] = mlflow_run_id

    # Register model version
    model_version = model_registry.register_model_version(
        name=name,
        version=version or "1",
        model_source_uri=model_source_uri,
        description=description,
        metadata=metadata,
    )

    logger.info(
        f"Registered model {name} "
        f"with version {model_version.version} "
        f"from source {model_source_uri}."
    )
