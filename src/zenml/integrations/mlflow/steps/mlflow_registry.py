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
"""Implementation of the MLflow model deployer pipeline step."""

from typing import Dict, Optional, cast

from mlflow.tracking import MlflowClient, artifact_utils

from zenml import __version__
from zenml.client import Client
from zenml.environment import Environment
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.mlflow_utils import (
    get_missing_mlflow_experiment_tracker_error,
)
from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistration,
    ModelVersion,
)
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseParameters,
    StepEnvironment,
    step,
)

logger = get_logger(__name__)


class MLFlowRegistryParameters(BaseParameters):
    """Model deployer step parameters for MLflow.

    Args:
        registered_model_name: Name of the registered model.
        registered_model_description: Description of the registered model.
        registered_model_tags: Tags to be added to the registered model.
        trained_model_name: Name of the model to be deployed.
        experiment_name: Name of the experiment to be used for the run.
        run_name: Name of the run to be created.
        run_id: ID of the run to be used.
        model_source_uri: URI of the model source. If not provided, the model
            will be fetched from the MLflow tracking server.
        description: Description of the model.
        tags: Tags to be added to the model.
    """

    registered_model_name: str
    registered_model_description: Optional[str] = None
    registered_model_tags: Optional[Dict[str, str]] = None
    trained_model_name: Optional[str] = "model"
    model_source_uri: Optional[str] = None
    experiment_name: Optional[str] = None
    run_name: Optional[str] = None
    run_id: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


@step(enable_cache=False)
def mlflow_register_model_step(
    run_id: str,
    params: MLFlowRegistryParameters,
) -> None:
    """MLflow model registry step.

    Args:
        run_id: ID of the run to be used.
        params: Parameters for the step.

    Raises:
        ValueError: If the model registry is not an MLflow model registry.
        get_missing_mlflow_experiment_tracker_error: If the experiment tracker
            is not an MLflow experiment tracker.
        ValueError: If no model source URI is provided and no model is found
    """
    # fetch the MLflow artifacts logged during the pipeline run
    experiment_tracker = Client().active_stack.experiment_tracker
    if not isinstance(experiment_tracker, MLFlowExperimentTracker):
        raise get_missing_mlflow_experiment_tracker_error()

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
    run_name = step_env.run_name
    step_name = step_env.step_name
    pipeline_run_id = step_env.pipeline_run_id

    client = MlflowClient()

    # Get MLflow run ID either from params or from experiment tracker using
    # pipeline name and run name
    # Note: We need to run the experiment tracker get_run_id() method
    # first, because it will persist the run ID in the experiment tracker.
    # not doing it causes a speriodic bug where the run ID is not found
    mlflow_run_id = (
        experiment_tracker.get_run_id(
            experiment_name=params.experiment_name or pipeline_name,
            run_name=params.run_name or run_name,
        )
        or params.run_id
    )
    if params.run_id and params.run_id != mlflow_run_id:
        mlflow_run_id = params.run_id
    # If no value was set at all, raise an error
    if not mlflow_run_id:
        raise ValueError(
            f"Could not find MLflow run for pipeline {pipeline_name} "
            f"and run {run_name} in experiment {params.experiment_name}."
        )
    # Lastly, check if the run ID is valid
    try:
        client.get_run(run_id=mlflow_run_id).info.run_id
    except Exception:
        raise ValueError(f"Could not find MLflow run with ID {mlflow_run_id}.")

    # Set model source URI
    model_source_uri = params.model_source_uri or None

    # Check if the run ID have a model artifact if no model source URI is set.
    if not params.model_source_uri and client.list_artifacts(
        mlflow_run_id, params.trained_model_name
    ):
        model_source_uri = artifact_utils.get_artifact_uri(
            run_id=mlflow_run_id, artifact_path=params.trained_model_name
        )
    if not model_source_uri:
        raise ValueError(
            "No model source URI provided and no model found in the "
            "MLflow tracking server for the given inputs."
        )

    # Add zenml tags
    tags = params.tags or {}
    tags["zenml_pipeline_name"] = pipeline_name
    tags["zenml_pipeline_run_id"] = pipeline_run_id
    tags["zenml_step_name"] = step_name
    tags["zenml_version"] = __version__

    # Create model registration
    model_registration = ModelRegistration(
        name=params.registered_model_name,
        description=params.registered_model_description,
        tags=params.registered_model_tags,
    )

    # Register model
    model_registry.register_model(model_registration)

    # Create model version
    model_version = ModelVersion(
        model_registration=model_registration,
        model_source_uri=model_source_uri,
        description=params.description,
        tags=tags,
    )

    # Register model version
    model_registry.register_model_version(model_version)

    logger.info(
        f"Registered model {params.registered_model_name} "
        f"with version {model_version.version} "
        f"from source {model_source_uri}."
    )
