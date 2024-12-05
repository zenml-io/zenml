# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from typing_extensions import Annotated

import zenml
from zenml import ArtifactConfig, get_step_context, step
from zenml.client import F, Client
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)

mlflow_enabled = False
try:
    from zenml.integrations.mlflow.experiment_trackers import (
        MLFlowExperimentTracker,
    )
    from zenml.integrations.mlflow.model_registries import (
        MLFlowModelRegistry,
    )

    mlflow_enabled = True
except ImportError:
    pass

logger = get_logger(__name__)

experiment_tracker = Client().active_stack.experiment_tracker

if mlflow_enabled:
    if not experiment_tracker or not isinstance(
        experiment_tracker, MLFlowExperimentTracker
    ):
        mlflow_enabled = False


@step(
    experiment_tracker=experiment_tracker.name if experiment_tracker else None,
    enable_cache=False,
)
def model_register(
    name: str = "model",
) -> Annotated[str, ArtifactConfig(name="model_registry_uri")]:
    """Register the model in the model registry.

    Args:
        name: The name of the model artifact in the current ZenML model.

    Returns:
        The URI of the registered model.
    """
    model_registry = Client().active_stack.model_registry
    model_source_uri = ""
    if model_registry:
        current_model = get_step_context().model

        # collect model metadata
        step_context = get_step_context()
        metadata = ModelRegistryModelMetadata()
        metadata.zenml_version = zenml.__version__
        metadata.zenml_pipeline_name = pipeline_name = (
            step_context.pipeline.name
        )
        metadata.zenml_run_name = current_run_name = (
            step_context.pipeline_run.name
        )
        metadata.zenml_pipeline_run_uuid = str(step_context.pipeline_run.id)
        metadata.zenml_workspace = str(model_registry.workspace)

        if mlflow_enabled:
            from mlflow.tracking import artifact_utils

            # get the experiment tracker and check if it is an MLflow experiment tracker.
            experiment_tracker = Client().active_stack.experiment_tracker
            if not isinstance(experiment_tracker, MLFlowExperimentTracker):
                raise ValueError(
                    "The MLflow model registry step can only be used with an "
                    "MLflow experiment tracker. Please add an MLflow experiment "
                    "tracker to your stack."
                )

            if not isinstance(model_registry, MLFlowModelRegistry):
                raise ValueError(
                    "The MLflow model registry step can only be used with an "
                    "MLflow model registry."
                )

            # Get MLflow run ID either from params or from experiment tracker using
            # pipeline name and run name
            mlflow_run_id = experiment_tracker.get_run_id(
                experiment_name=pipeline_name,
                run_name=current_run_name,
            )
            # If no value was set at all, raise an error
            if not mlflow_run_id:
                raise RuntimeError(
                    f"Could not find MLflow run for experiment {pipeline_name} "
                    f"and run {current_run_name}."
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

            # Check if the run ID have a model artifact if no model source URI is set.
            if client.list_artifacts(mlflow_run_id, "model"):
                model_source_uri = artifact_utils.get_artifact_uri(  # type: ignore[no-untyped-call]
                    run_id=mlflow_run_id, artifact_path="model"
                )
            if not model_source_uri:
                raise RuntimeError(
                    "No model source URI provided or no model found in the "
                    "MLflow tracking server for the given inputs."
                )

            setattr(metadata, "mlflow_run_id", mlflow_run_id)
        else:
            model_source_uri = current_model.get_model_artifact(name).uri

        # Register model version
        model_version = model_registry.register_model_version(
            name=current_model.name,
            version=str(current_model.version),
            model_source_uri=model_source_uri,
            metadata=metadata,
        )
        current_model.log_metadata(
            {"model_registry_version": model_version.version}
        )

        model_source_uri = model_version.model_source_uri

        logger.info(
            f"Registered model {current_model.name} "
            f"with version {model_version.version} "
            f"from source {model_source_uri}."
        )

    return model_source_uri
