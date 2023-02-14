#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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


from typing import Any, Dict, List, Optional, Tuple, cast

from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from mlflow.pyfunc import load_model

from zenml import __version__
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_model_registry_flavor import (
    MLFlowModelRegistryConfig,
)
from zenml.integrations.mlflow.mlflow_utils import (
    get_missing_mlflow_experiment_tracker_error,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistration,
    ModelVersion,
    ModelVersionStage,
)
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator

logger = get_logger(__name__)


class MLFlowModelRegistry(BaseModelRegistry):
    """Track experiments using MLflow."""

    _client: Optional[MlflowClient] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the experiment tracker and validate the tracking uri.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

    @property
    def config(self) -> MLFlowModelRegistryConfig:
        """Returns the `MLFlowModelRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(MLFlowModelRegistryConfig, self._config)

    @property
    def mlflow_client(self) -> MlflowClient:
        """Get the MLFlow client.

        Raises:
            get_missing_mlflow_experiment_tracker_error: If the stack does not
                contain an MLFlow experiment tracker.

        Returns:
            The MLFlowClient.
        """
        if not self._client:
            # TODO: can this be done in a better way?
            experiment_tracker = Client().active_stack.experiment_tracker
            if not isinstance(experiment_tracker, MLFlowExperimentTracker):
                raise get_missing_mlflow_experiment_tracker_error()
            experiment_tracker.configure_mlflow()
            self._client = MlflowClient()
        return self._client

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains an mlflow experiment tracker.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that the experiment tracker is an mlflow experiment tracker.

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
                    "The MLFlow model registry requires a MLFlow experiment "
                    "tracker. You should register a MLFlow experiment "
                    "tracker to the stack using the following command: "
                    "`zenml stack register experiment_tracker ..."
                )
            experiment_tracker
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
    ) -> ModelRegistration:
        """Register a model to the MLFlow model registry.

        Args:
            name (str): The name of the model.
            description (str, optional): The description of the model.
            tags (Dict, optional): The tags of the model.

        Raises:
            MlflowException: If the model already exists.
            KeyError: If the model already exists.

        Returns:
            The registered model.
        """
        # Check if model already exists.
        if self.check_model_exists(name):
            raise KeyError(
                f"Model with name {name} already exists in the MLFlow model "
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
            logger.error(
                f"Failed to register model with name {name} to MLFlow model "
                f"registry.",
            )
            raise e
        # Return the registered model.
        return ModelRegistration(
            name=registered_model.name,
            description=registered_model.description,
            tags=registered_model.tags,
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from the MLFlow model registry.

        Args:
            name (str): The name of the model.

        Raises:
            MlflowException: If the model does not exist.
            KeyError: If the model does not exist.
        """
        # Check if model exists.
        if not self.check_model_exists(name):
            raise KeyError(
                f"Model with name {name} does not exist in the MLFlow model "
                f"registry.",
            )
        # Delete the registered model.
        try:
            self.mlflow_client.delete_registered_model(
                name=name,
            )
        except MlflowException as e:
            logger.error(
                f"Failed to delete model with name {name} from MLFlow model "
                f"registry.",
            )
            raise e

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelRegistration:
        """Update a model in the MLFlow model registry.

        Args:
            name (str): The name of the model.
            description (str, optional): The description of the model.
            tags (Dict, optional): The tags of the model.

        Raises:
            MlflowException: If mlflow fails to update the model.
            KeyError: If the model does not exist.

        Returns:
            The updated model.
        """
        # Check if model exists.
        if not self.check_model_exists(name):
            raise KeyError(
                f"Model with name {name} does not exist in the MLFlow model "
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
                logger.error(
                    f"Failed to update description for the model {name} in MLFlow"
                    f" model registry.",
                )
                raise e
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
                logger.error(
                    f"Failed to update tags for the model {name} in MLFlow model "
                    f"registry.",
                )
                raise e
        # Return the updated registered model.
        return self.get_model(name)

    def get_model(self, name: str) -> ModelRegistration:
        """Get a model from the MLFlow model registry.

        Args:
            name: The name of the model.

        Returns:
            The model.

        Raises:
            MlflowException: If mlflow fails to get the model.
        """
        # Get the registered model.
        try:
            registered_model = self.mlflow_client.get_registered_model(
                name=name,
            )
        except MlflowException as e:
            logger.error(
                f"Failed to get model with name {name} from the MLFlow model "
                f"registry.",
            )
            raise e
        # Return the registered model.
        return ModelRegistration(
            name=registered_model.name,
            description=registered_model.description,
            tags=registered_model.tags,
        )

    def list_models(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[ModelRegistration]:
        """List models in the MLFlow model registry.

        Args:
            name (str, optional): A name to filter the models by.
            tags (dict, optional): The tags to filter the models by.

        Returns:
            A list of models (ModelRegistration)
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
            ModelRegistration(
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
        """Check if a model exists in the MLFlow model registry.

        Args:
            name (str): The name of the model.

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
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        model_source_uri: Optional[str] = None,
        version: Optional[str] = None,
        version_description: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        registry_metadata: Optional[Dict[str, str]] = None,
        zenml_version: Optional[str] = None,
        zenml_pipeline_run_id: Optional[str] = None,
        zenml_pipeline_name: Optional[str] = None,
        zenml_step_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelVersion:
        """Register a model version to the MLFlow model registry.

        Args:
            name (str): The name of the model.
            description (str, optional): The description of the model.
            tags (Dict, optional): The tags of the model.
            model_source_uri (str, optional): The source URI of the model.
            version (str, optional): The version of the model.
            version_description (str, optional): The description of the model
                version.
            version_tags (Dict, optional): The tags of the model version.
            registry_metadata (Dict, optional): The registry metadata of the
                model version.
            zenml_version (str, optional): The ZenML version.
            zenml_pipeline_run_id (str, optional): The ZenML pipeline run ID.
            zenml_pipeline_name (str, optional): The ZenML pipeline name.
            zenml_step_name (str, optional): The ZenML step name.
            **kwargs: Additional keyword arguments.

        Raises:
            MlflowException: If the registered model does not exist.

        Returns:
            The registered model version.
        """
        # Check if the model exists, if not create it.
        if not self.check_model_exists(name):
            logger.warning(
                f"No registered model with name {name} found. Creating a new"
                "registered model."
            )
            self.register_model(
                name=name,
                description=description,
                tags=tags,
            )
        try:
            # Inform the user that the version is ignored.
            if version:
                logger.info(
                    f"MLFlow model registry does not take a version as an argument. "
                    f"Registering a new version for the model `'{name}'` "
                    f"a version will be assigned automatically."
                )
            # Set the tags.
            if not version_tags:
                version_tags = {}
            version_tags["zenml_version"] = zenml_version or __version__
            version_tags["zenml_pipeline_run_id"] = zenml_pipeline_run_id or ""
            version_tags["zenml_pipeline_name"] = zenml_pipeline_name or ""
            version_tags["zenml_step_name"] = zenml_step_name or ""
            # Register the model version.
            registered_model_version = self.mlflow_client.create_model_version(
                name=name,
                source=model_source_uri,
                run_id=registry_metadata.get("mlflow_run_id")
                if registry_metadata
                else "",
                run_link=registry_metadata.get("mlflow_run_link")
                if registry_metadata
                else "",
                description=version_description,
                tags=version_tags,
            )
        except MlflowException as e:
            logger.error(
                f"Failed to register new model version for model '{name}'."
            )
            raise e
        # Return the registered model version.
        return ModelVersion(
            model_registration=ModelRegistration(
                name=registered_model_version.name,
                description=description,
                tags=tags,
            ),
            model_source_uri=registered_model_version.source,
            registry_metadata={
                "mlflow_run_id": registered_model_version.run_id or "",
                "mlflow_run_link": registered_model_version.run_link or "",
            },
            version=registered_model_version.version,
            description=registered_model_version.description,
            version_stage=registered_model_version.current_stage,
            tags=registered_model_version.tags,
            created_at=str(registered_model_version.creation_timestamp),
            last_updated_at=str(
                registered_model_version.last_updated_timestamp
            ),
        )

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version (str): The version of the model.

        Raises:
            MlflowException: If mlflow fails to delete the model version.
            KeyError: If the model version does not exist.
        """
        if not self.check_model_version_exists(name, version):
            raise KeyError(
                f"The model version with name '{name}' and version '{version}' "
                "does not exist."
            )
        try:
            self.mlflow_client.delete_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            logger.error(
                f"Failed to delete model version '{name}:{version}' from the "
                "MLFlow model registry."
            )
            raise e

    def update_model_version(
        self,
        name: str,
        version: str,
        version_description: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        version_stage: Optional[ModelVersionStage] = None,
    ) -> ModelVersion:
        """Update a model version in the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version (str): The version of the model.
            version_description (str, optional): The description of the model version.
            version_tags (dict, optional): The tags of the model version.
            version_stage (ModelVersionStage, Optional): The stage of the model version.

        Raises:
            MlflowException: If mlflow fails to update the model version.
            KeyError: If the model version does not exist.

        Returns:
            The updated model version.
        """
        if not self.check_model_version_exists(name, version):
            raise KeyError(
                f"The model version with name '{name}' and version '{version}' "
                "does not exist."
            )
        # Update the model description.
        if version_description:
            try:
                self.mlflow_client.update_model_version(
                    name=name,
                    version=version,
                    description=version_description,
                )
            except MlflowException as e:
                logger.error(
                    f"Failed to update the description of model version "
                    f"'{name}:{version}' in the MLFlow model registry."
                )
                raise e
        # Update the model tags.
        if version_tags:
            try:
                for key, value in version_tags.items():
                    self.mlflow_client.set_model_version_tag(
                        name=name,
                        version=version,
                        key=key,
                        value=value,
                    )
            except MlflowException as e:
                logger.error(
                    f"Failed to update the tags of model version "
                    f"'{name}:{version}' in the MLFlow model registry."
                )
                raise e
        # Update the model stage.
        if version_stage:
            try:
                self.mlflow_client.transition_model_version_stage(
                    name=name,
                    version=version,
                    stage=version_stage.value,
                )
            except MlflowException as e:
                logger.error(
                    f"Failed to update the stage of model version "
                    f"'{name}:{version}' in the MLFlow model registry."
                )
                raise e
        return self.get_model_version(name, version)

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> ModelVersion:
        """Get a model version from the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version (str): The version of the model.

        Raises:
            MlflowException: If mlflow fails to get the model version.

        Returns:
            The model version.
        """
        # Get the model version from the MLFlow model registry.
        try:
            mlflow_model_version = self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            logger.error(
                f"Failed to get model version '{name}:{version}' from the "
                "MLFlow model registry."
            )
            raise e
        # Return the model version.
        return ModelVersion(
            model_registration=ModelRegistration(
                name=mlflow_model_version.name
            ),
            version=mlflow_model_version.version,
            created_at=str(mlflow_model_version.creation_timestamp),
            version_stage=ModelVersionStage(
                mlflow_model_version.current_stage
            ),
            version_description=mlflow_model_version.description,
            last_updated_at=str(mlflow_model_version.last_updated_timestamp),
            registry_metadata={
                "mlflow_run_id": mlflow_model_version.run_id or "",
                "mlflow_run_link": mlflow_model_version.run_link or "",
            },
            model_source_uri=mlflow_model_version.source,
            version_tags=mlflow_model_version.tags,
        )

    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        version_tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[ModelVersion]:
        """List model versions from the MLFlow model registry.

        Args:
            name (str, optional): The name of the model.
            model_source_uri (str, optional): The model source URI.
            version_tags (dict, optional): The tags of the model version.
            kwargs (dict, optional): Additional keyword arguments.

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
        if version_tags:
            for tag, value in version_tags.items():
                if filter_string:
                    filter_string += " AND "
                filter_string += f"tags.{tag}='{value}'"
        # Get the model versions.
        mlflow_model_versions = self.mlflow_client.search_model_versions(
            filter_string=filter_string,
        )
        # Return the model versions.
        return [
            ModelVersion(
                model_registration=ModelRegistration(
                    name=mlflow_model_version.name
                ),
                version=mlflow_model_version.version,
                created_at=str(mlflow_model_version.creation_timestamp),
                version_stage=ModelVersionStage(
                    mlflow_model_version.current_stage
                ),
                version_description=mlflow_model_version.description,
                last_updated_at=str(
                    mlflow_model_version.last_updated_timestamp
                ),
                registry_metadata={
                    "mlflow_run_id": mlflow_model_version.run_id or "",
                    "mlflow_run_link": mlflow_model_version.run_link or "",
                },
                model_source_uri=mlflow_model_version.source,
                version_tags=mlflow_model_version.tags,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def get_latest_model_versions(
        self,
        name: str,
        version_stages: Optional[List[ModelVersionStage]] = None,
    ) -> List[ModelVersion]:
        """Get the latest model versions from the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version_stages (list, optional): The stages of the model version.

        Returns:
            The latest model versions or None if no model versions exist.

        Raises:
            KeyError: If the model does not exist.
        """
        if self.check_model_exists(name):
            raise KeyError(f"Model '{name}' does not exist.")
        # Get the latest model versions.
        stages = (
            [version_stage.value for version_stage in version_stages]
            if version_stages
            else None
        )
        mlflow_model_versions = self.mlflow_client.get_latest_versions(
            name=name,
            stages=stages,
        )
        # Return the model versions.
        return [
            ModelVersion(
                model_registration=ModelRegistration(
                    name=mlflow_model_version.name
                ),
                version=mlflow_model_version.version,
                created_at=str(mlflow_model_version.creation_timestamp),
                version_stage=ModelVersionStage(
                    mlflow_model_version.current_stage
                ),
                version_description=mlflow_model_version.description,
                last_updated_at=str(
                    mlflow_model_version.last_updated_timestamp
                ),
                registry_metadata={
                    "mlflow_run_id": mlflow_model_version.run_id or "",
                    "mlflow_run_link": mlflow_model_version.run_link or "",
                },
                model_source_uri=mlflow_model_version.source,
                version_tags=mlflow_model_version.tags,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def check_model_version_exists(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Check if a model version exists in the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version (str): The version of the model.

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
        """Load a model version from the MLFlow model registry.

        Args:
            name (str): The name of the model.
            version (str): The version of the model.
            kwargs (dict, optional): Additional keyword arguments.

        Returns:
            The model version.

        Raises:
            KeyError: If the model version does not exist.
        """
        if not self.check_model_version_exists(name, version):
            raise KeyError(f"Model version '{name}:{version}' does not exist.")
        # Load the model version.
        mlflow_model_version = self.mlflow_client.get_model_version(
            name=name,
            version=version,
        )
        return load_model(
            model_uri=mlflow_model_version.source,
            **kwargs,
        )
