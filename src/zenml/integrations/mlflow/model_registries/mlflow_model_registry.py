#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the MLflow model registry for ZenML."""


from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import mlflow
from mlflow import MlflowClient
from mlflow.entities.model_registry import ModelVersion as MLflowModelVersion
from mlflow.exceptions import MlflowException
from mlflow.pyfunc import load_model
from pydantic import Field

from zenml import __version__
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.exceptions import EntityExistsError
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_model_registry_flavor import (
    MLFlowModelRegistryConfig,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistryModelMetadata,
    ModelVersion,
    ModelVersionStage,
    RegisteredModel,
)
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator

logger = get_logger(__name__)


class MLFlowModelRegistry(BaseModelRegistry):
    """Register models using MLflow."""

    _client: Optional[MlflowClient] = None

    @property
    def config(self) -> MLFlowModelRegistryConfig:
        """Returns the `MLFlowModelRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(MLFlowModelRegistryConfig, self._config)

    def configure_mlflow(self) -> None:
        """Configures the MLflow Client with the experiment tracker config."""
        experiment_tracker = Client().active_stack.experiment_tracker
        assert isinstance(experiment_tracker, MLFlowExperimentTracker)
        experiment_tracker.configure_mlflow()

    @property
    def mlflow_client(self) -> MlflowClient:
        """Get the MLflow client.

        Returns:
            The MLFlowClient.
        """
        if not self._client:
            self.configure_mlflow()
            self._client = mlflow.tracking.MlflowClient()
        return self._client

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains an mlflow experiment tracker.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that all the requirements are met for the stack.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple of (is_valid, error_message).
            """
            # Validate that the experiment tracker is an mlflow experiment tracker.
            experiment_tracker = stack.experiment_tracker
            assert experiment_tracker is not None
            if experiment_tracker.flavor != "mlflow":
                return False, (
                    "The MLflow model registry requires a MLflow experiment "
                    "tracker. You should register a MLflow experiment "
                    "tracker to the stack using the following command: "
                    "`zenml stack update model_registry -e mlflow_tracker"
                )
            mlflow_version = mlflow.version.VERSION
            if (
                not mlflow_version >= "2.1.1"
                and experiment_tracker.config.is_local
            ):
                return False, (
                    "The MLflow model registry requires MLflow version "
                    f"2.1.1 or higher to use a local MLflow registry. "
                    f"Your current MLflow version is {mlflow_version}."
                    "You can upgrade MLflow using the following command: "
                    "`pip install --upgrade mlflow`"
                )
            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.EXPERIMENT_TRACKER,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    # ---------
    # Model Registration Methods
    # ---------

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model to the MLflow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            tags: The tags of the model.

        Raises:
            RuntimeError: If the model already exists.
            EntityExistsError: If the model already exists.

        Returns:
            The registered model.
        """
        # Check if model already exists.
        if self.check_model_exists(name):
            raise EntityExistsError(
                f"Model with name {name} already exists in the MLflow model "
                f"registry.",
            )
        # Register model.
        try:
            registered_model = self.mlflow_client.create_registered_model(
                name=name,
                description=description,
                tags=tags,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to register model with name {name} to the MLflow "
                f"model registry: {str(e)}",
            )

        # Return the registered model.
        return RegisteredModel(
            name=registered_model.name,
            description=registered_model.description,
            tags=registered_model.tags,
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from the MLflow model registry.

        Args:
            name: The name of the model.

        Raises:
            RuntimeError: If the model does not exist.
            EntityExistsError: If the model does not exist.
        """
        # Check if model exists.
        if not self.check_model_exists(name):
            raise EntityExistsError(
                f"Model with name {name} does not exist in the MLflow model "
                f"registry.",
            )
        # Delete the registered model.
        try:
            self.mlflow_client.delete_registered_model(
                name=name,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to delete model with name {name} from MLflow model "
                f"registry: {str(e)}",
            )

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        remove_tags: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Update a model in the MLflow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            tags: The tags of the model.
            remove_tags: The tags to remove from the model.

        Raises:
            RuntimeError: If mlflow fails to update the model.
            EntityExistsError: If the model does not exist.

        Returns:
            The updated model.
        """
        # Check if model exists.
        if not self.check_model_exists(name):
            raise EntityExistsError(
                f"Model with name {name} does not exist in the MLflow model "
                f"registry.",
            )
        # Update the registered model description.
        if description:
            try:
                self.mlflow_client.update_registered_model(
                    name=name,
                    description=description,
                )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to update description for the model {name} in MLflow "
                    f"model registry: {str(e)}",
                )
        # Update the registered model tags.
        if tags:
            try:
                for tag, value in tags.items():
                    self.mlflow_client.set_registered_model_tag(
                        name=name,
                        key=tag,
                        value=value,
                    )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to update tags for the model {name} in MLflow model "
                    f"registry: {str(e)}",
                )
        # Remove tags from the registered model.
        if remove_tags:
            try:
                for tag in remove_tags:
                    self.mlflow_client.delete_registered_model_tag(
                        name=name,
                        key=tag,
                    )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to remove tags for the model {name} in MLflow model "
                    f"registry: {str(e)}",
                )
        # Return the updated registered model.
        return self.get_model(name)

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from the MLflow model registry.

        Args:
            name: The name of the model.

        Returns:
            The model.

        Raises:
            RuntimeError: If mlflow fails to get the model.
            EntityExistsError: If the model does not exist.
        """
        # Get the registered model.
        try:
            registered_model = self.mlflow_client.get_registered_model(
                name=name,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to get model with name {name} from the MLflow model "
                f"registry: {str(e)}",
            )
        # Return the registered model.
        return RegisteredModel(
            name=registered_model.name,
            description=registered_model.description,
            tags=registered_model.tags,
        )

    def list_models(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the MLflow model registry.

        Args:
            name: A name to filter the models by.
            tags: The tags to filter the models by.

        Returns:
            A list of models (RegisteredModel)
        """
        # Set the filter string.
        filter_string = ""
        if name:
            filter_string += f"name='{name}'"
        if tags:
            for tag, value in tags.items():
                if filter_string:
                    filter_string += " AND "
                filter_string += f"tags.{tag}='{value}'"

        # Get the registered models.
        registered_models = self.mlflow_client.search_registered_models(
            filter_string=filter_string,
            max_results=100,
        )
        # Return the registered models.
        return [
            RegisteredModel(
                name=registered_model.name,
                description=registered_model.description,
                tags=registered_model.tags,
            )
            for registered_model in registered_models
        ]

    def check_model_exists(
        self,
        name: str,
    ) -> bool:
        """Check if a model exists in the MLflow model registry.

        Args:
            name: The name of the model.

        Returns:
            True if the model exists, False otherwise.
        """
        # Check if the model exists.
        try:
            self.mlflow_client.get_registered_model(name=name)
        except MlflowException:
            return False
        return True

    # ---------
    # Model Version Methods
    # ---------

    def register_model_version(
        self,
        name: str,
        version: str,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: ModelRegistryModelMetadata = Field(
            default_factory=ModelRegistryModelMetadata
        ),
        **kwargs: Any,
    ) -> ModelVersion:
        """Register a model version to the MLflow model registry.

        Args:
            name: The name of the model.
            model_source_uri: The source URI of the model.
            version: The version of the model.
            description: The description of the model version.
            tags: The tags of the model version.
            metadata: The registry metadata of the model version.
            **kwargs: Additional keyword arguments.

        Raises:
            RuntimeError: If the registered model does not exist.

        Returns:
            The registered model version.
        """
        # Check if the model exists, if not create it.
        if not self.check_model_exists(name):
            logger.info(
                f"No registered model with name {name} found. Creating a new"
                "registered model."
            )
            self.register_model(
                name=name,
            )
        try:
            # Inform the user that the version is ignored.
            logger.info(
                f"MLflow model registry does not take a version as an argument. "
                f"Registering a new version for the model `'{name}'` "
                f"a version will be assigned automatically."
            )
            # Set the tags.
            tags = tags or {}
            tags["zenml_version"] = metadata.zenml_version or __version__
            if metadata.zenml_pipeline_run_id:
                tags["zenml_pipeline_run_id"] = metadata.zenml_pipeline_run_id
            if metadata.zenml_pipeline_name:
                tags["zenml_pipeline_name"] = metadata.zenml_pipeline_name
            if metadata.zenml_step_name:
                tags["zenml_step_name"] = metadata.zenml_step_name
            if metadata.zenml_workspace:
                tags["zenml_workspace"] = metadata.zenml_workspace
            if metadata.zenml_pipeline_run_uuid:
                tags[
                    "zenml_pipeline_run_uuid"
                ] = metadata.zenml_pipeline_run_uuid
            if metadata.zenml_pipeline_uuid:
                tags["zenml_pipeline_uuid"] = metadata.zenml_pipeline_uuid
            # Set the run ID and link.
            run_id = metadata.dict().get("mlflow_run_id", None)
            run_link = metadata.dict().get("mlflow_run_link", None)
            # Register the model version.
            registered_model_version = self.mlflow_client.create_model_version(
                name=name,
                source=model_source_uri,
                run_id=run_id,
                run_link=run_link,
                description=description,
                tags=tags,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to register model version with name '{name}' and "
                f"version '{version}' to the MLflow model registry."
                f"Error: {e}"
            )
        # Return the registered model version.
        return self._cast_mlflow_version_to_model_version(
            registered_model_version
        )

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            RuntimeError: If mlflow fails to delete the model version.
            EntityExistsError: If the model version does not exist.
        """
        if not self.check_model_version_exists(name, version):
            raise EntityExistsError(
                f"The model version with name '{name}' and version '{version}' "
                "does not exist."
            )
        try:
            self.mlflow_client.delete_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to delete model version '{version}' of model '{name}'."
                f"From the MLflow model registry: {str(e)}",
            )

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        remove_tags: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> ModelVersion:
        """Update a model version in the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            description: The description of the model version.
            tags: The tags of the model version.
            remove_tags: The tags to remove from the model version.
            stage: The stage of the model version.

        Raises:
            RuntimeError: If mlflow fails to update the model version.
            EntityExistsError: If the model version does not exist.

        Returns:
            The updated model version.
        """
        if not self.check_model_version_exists(name, version):
            raise EntityExistsError(
                f"The model version with name '{name}' and version '{version}' "
                "does not exist."
            )
        # Update the model description.
        if description:
            try:
                self.mlflow_client.update_model_version(
                    name=name,
                    version=version,
                    description=description,
                )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to update the description of model version "
                    f"'{name}:{version}' in the MLflow model registry: {str(e)}"
                )
        # Update the model tags.
        if tags:
            try:
                for key, value in tags.items():
                    self.mlflow_client.set_model_version_tag(
                        name=name,
                        version=version,
                        key=key,
                        value=value,
                    )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to update the tags of model version "
                    f"'{name}:{version}' in the MLflow model registry: {str(e)}"
                )
        # Remove the model tags.
        if remove_tags:
            try:
                for key in remove_tags:
                    self.mlflow_client.delete_model_version_tag(
                        name=name,
                        version=version,
                        key=key,
                    )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to remove the tags of model version "
                    f"'{name}:{version}' in the MLflow model registry: {str(e)}"
                )
        # Update the model stage.
        if stage:
            try:
                self.mlflow_client.transition_model_stage(
                    name=name,
                    version=version,
                    stage=stage.value,
                )
            except MlflowException as e:
                raise RuntimeError(
                    f"Failed to update the current stage of model version "
                    f"'{name}:{version}' in the MLflow model registry: {str(e)}"
                )
        return self.get_model_version(name, version)

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> ModelVersion:
        """Get a model version from the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            RuntimeError: If mlflow fails to get the model version.

        Returns:
            The model version.
        """
        # Get the model version from the MLflow model registry.
        try:
            mlflow_model_version = self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            raise RuntimeError(
                f"Failed to get model version '{name}:{version}' from the "
                f"MLflow model registry: {str(e)}"
            )
        # Return the model version.
        return self._cast_mlflow_version_to_model_version(
            mlflow_model_version=mlflow_model_version,
        )

    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[ModelVersion]:
        """List model versions from the MLflow model registry.

        Args:
            name: The name of the model.
            model_source_uri: The model source URI.
            tags: The tags of the model version.
            kwargs: Additional keyword arguments.

        Returns:
            The model versions.
        """
        # Set the filter string.
        filter_string = ""
        if name:
            filter_string += f"name='{name}'"
        if model_source_uri:
            if filter_string:
                filter_string += " AND "
            filter_string += f"source='{model_source_uri}'"
        if "mlflow_run_id" in kwargs and kwargs["mlflow_run_id"]:
            if filter_string:
                filter_string += " AND "
            filter_string += f"run_id='{kwargs['mlflow_run_id']}'"
        if tags:
            for tag, value in tags.items():
                if filter_string:
                    filter_string += " AND "
                filter_string += f"tags.{tag}='{value}'"
        # Get the model versions.
        mlflow_model_versions = self.mlflow_client.search_model_versions(
            filter_string=filter_string,
        )
        # Return the model versions.
        return [
            self._cast_mlflow_version_to_model_version(
                mlflow_model_version=mlflow_model_version,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def get_latest_model_versions(
        self,
        name: str,
        stages: Optional[List[ModelVersionStage]] = None,
    ) -> List[ModelVersion]:
        """Get the latest model versions from the MLflow model registry.

        Args:
            name: The name of the model.
            stages: The stages of the model version.

        Returns:
            The latest model versions.

        Raises:
            EntityExistsError: If the model does not exist.
        """
        if self.check_model_exists(name):
            raise EntityExistsError(f"Model '{name}' does not exist.")
        # Get the latest model versions.
        model_version_stages = (
            [stage.value for stage in stages] if stages else None
        )
        mlflow_model_versions = self.mlflow_client.get_latest_versions(
            name=name,
            stages=model_version_stages,
        )
        # Return the model versions.
        return [
            self._cast_mlflow_version_to_model_version(
                mlflow_model_version=mlflow_model_version,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def check_model_version_exists(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Check if a model version exists in the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            True if the model version exists, False otherwise.
        """
        # Check if the model version exists.
        try:
            self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
        except MlflowException:
            return False
        return True

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            kwargs: Additional keyword arguments.

        Returns:
            The model version.

        Raises:
            EntityExistsError: If the model version does not exist.
        """
        if not self.check_model_version_exists(name, version):
            raise EntityExistsError(
                f"Model version '{name}:{version}' does not exist."
            )
        # Load the model version.
        mlflow_model_version = self.mlflow_client.get_model_version(
            name=name,
            version=version,
        )
        return load_model(
            model_uri=mlflow_model_version.source,
            **kwargs,
        )

    def _cast_mlflow_version_to_model_version(
        self,
        mlflow_model_version: MLflowModelVersion,
    ) -> ModelVersion:
        """Cast an MLflow model version to a model version.

        Args:
            mlflow_model_version: The MLflow model version.

        Returns:
            The model version.
        """
        metadata = {}
        if mlflow_model_version.run_id:
            metadata["mlflow_run_id"] = mlflow_model_version.run_id
        if mlflow_model_version.run_link:
            metadata["mlflow_run_link"] = mlflow_model_version.run_link
        return ModelVersion(
            model_registration=RegisteredModel(name=mlflow_model_version.name),
            version=mlflow_model_version.version,
            created_at=datetime.fromtimestamp(
                int(mlflow_model_version.creation_timestamp) / 1e3
            ),
            stage=ModelVersionStage(mlflow_model_version.current_stage),
            description=mlflow_model_version.description,
            last_updated_at=datetime.fromtimestamp(
                int(mlflow_model_version.last_updated_timestamp) / 1e3
            ),
            metadata=ModelRegistryModelMetadata(**metadata),
            model_source_uri=mlflow_model_version.source,
            tags=mlflow_model_version.tags,
        )
