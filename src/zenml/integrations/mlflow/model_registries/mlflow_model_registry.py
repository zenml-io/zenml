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
from mlflow.entities.model_registry import (
    ModelVersion as MLflowModelVersion,
)
from mlflow.exceptions import MlflowException
from mlflow.pyfunc import load_model

from zenml.client import Client
from zenml.constants import MLFLOW_MODEL_FORMAT
from zenml.enums import StackComponentType
from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import (
    MLFlowExperimentTrackerConfig,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistryModelMetadata,
    ModelVersionStage,
    RegisteredModel,
    RegistryModelVersion,
)
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator

logger = get_logger(__name__)


class MLFlowModelRegistry(BaseModelRegistry):
    """Register models using MLflow."""

    _client: Optional[MlflowClient] = None

    @property
    def config(self) -> MLFlowExperimentTrackerConfig:
        """Returns the `MLFlowExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        experiment_tracker = Client().active_stack.experiment_tracker
        assert isinstance(experiment_tracker, MLFlowExperimentTracker)
        return cast(MLFlowExperimentTrackerConfig, experiment_tracker.config)

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
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model to the MLflow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.

        Raises:
            RuntimeError: If the model already exists.

        Returns:
            The registered model.
        """
        # Check if model already exists.
        try:
            self.get_model(name)
            raise KeyError(
                f"Model with name {name} already exists in the MLflow model "
                f"registry. Please use a different name.",
            )
        except KeyError:
            pass
        # Register model.
        try:
            registered_model = self.mlflow_client.create_registered_model(
                name=name,
                description=description,
                tags=metadata,
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
            metadata=registered_model.tags,
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
        """
        # Check if model exists.
        self.get_model(name=name)
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
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Update a model in the MLflow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.
            remove_metadata: The metadata to remove from the model.

        Raises:
            RuntimeError: If mlflow fails to update the model.

        Returns:
            The updated model.
        """
        # Check if model exists.
        self.get_model(name=name)
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
        if metadata:
            try:
                for tag, value in metadata.items():
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
        if remove_metadata:
            try:
                for tag in remove_metadata:
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
            KeyError: If mlflow fails to get the model.
        """
        # Get the registered model.
        try:
            registered_model = self.mlflow_client.get_registered_model(
                name=name,
            )
        except MlflowException as e:
            raise KeyError(
                f"Failed to get model with name {name} from the MLflow model "
                f"registry: {str(e)}",
            )
        # Return the registered model.
        return RegisteredModel(
            name=registered_model.name,
            description=registered_model.description,
            metadata=registered_model.tags,
        )

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the MLflow model registry.

        Args:
            name: A name to filter the models by.
            metadata: The metadata to filter the models by.

        Returns:
            A list of models (RegisteredModel)
        """
        # Set the filter string.
        filter_string = ""
        if name:
            filter_string += f"name='{name}'"
        if metadata:
            for tag, value in metadata.items():
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
                metadata=registered_model.tags,
            )
            for registered_model in registered_models
        ]

    # ---------
    # Model Version Methods
    # ---------

    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> RegistryModelVersion:
        """Register a model version to the MLflow model registry.

        Args:
            name: The name of the model.
            model_source_uri: The source URI of the model.
            version: The version of the model.
            description: The description of the model version.
            metadata: The registry metadata of the model version.
            **kwargs: Additional keyword arguments.

        Raises:
            RuntimeError: If the registered model does not exist.

        Returns:
            The registered model version.
        """
        # Check if the model exists, if not create it.
        try:
            self.get_model(name=name)
        except KeyError:
            logger.info(
                f"No registered model with name {name} found. Creating a new "
                "registered model."
            )
            self.register_model(
                name=name,
            )
        try:
            # Inform the user that the version is ignored.
            if version:
                logger.info(
                    f"MLflow model registry does not take a version as an argument. "
                    f"Registering a new version for the model `'{name}'` "
                    f"a version will be assigned automatically."
                )
            metadata_dict = metadata.model_dump() if metadata else {}
            # Set the run ID and link.
            run_id = metadata_dict.get("mlflow_run_id", None)
            run_link = metadata_dict.get("mlflow_run_link", None)
            # Register the model version.
            registered_model_version = self.mlflow_client.create_model_version(
                name=name,
                source=model_source_uri,
                run_id=run_id,
                run_link=run_link,
                description=description,
                tags=metadata_dict,
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
        """
        self.get_model_version(name=name, version=version)
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
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        """Update a model version in the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            description: The description of the model version.
            metadata: The metadata of the model version.
            remove_metadata: The metadata to remove from the model version.
            stage: The stage of the model version.

        Raises:
            RuntimeError: If mlflow fails to update the model version.

        Returns:
            The updated model version.
        """
        self.get_model_version(name=name, version=version)
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
        if metadata:
            try:
                for key, value in metadata.model_dump().items():
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
        if remove_metadata:
            try:
                for key in remove_metadata:
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
                self.mlflow_client.transition_model_version_stage(
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
    ) -> RegistryModelVersion:
        """Get a model version from the MLflow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            KeyError: If the model version does not exist.

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
            raise KeyError(
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
        metadata: Optional[ModelRegistryModelMetadata] = None,
        stage: Optional[ModelVersionStage] = None,
        count: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        order_by_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[RegistryModelVersion]:
        """List model versions from the MLflow model registry.

        Args:
            name: The name of the model.
            model_source_uri: The model source URI.
            metadata: The metadata of the model version.
            stage: The stage of the model version.
            count: The maximum number of model versions to return.
            created_after: The minimum creation time of the model versions.
            created_before: The maximum creation time of the model versions.
            order_by_date: The order of the model versions by creation time,
                either ascending or descending.
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
        if metadata:
            for tag, value in metadata.model_dump().items():
                if value:
                    if filter_string:
                        filter_string += " AND "
                    filter_string += f"tags.{tag}='{value}'"
                    # Get the model versions.
        order_by = []
        if order_by_date:
            if order_by_date in ["asc", "desc"]:
                if order_by_date == "asc":
                    order_by = ["creation_timestamp ASC"]
                else:
                    order_by = ["creation_timestamp DESC"]

        if self.config.enable_unity_catalog is True:
            mlflow_model_versions = self.mlflow_client.search_model_versions(
                filter_string=filter_string,
            )
        else:
            mlflow_model_versions = self.mlflow_client.search_model_versions(
                filter_string=filter_string,
                order_by=order_by,
            )
        # Cast the MLflow model versions to the ZenML model version class.
        model_versions = []
        for mlflow_model_version in mlflow_model_versions:
            # check if given MlFlow model version matches the given request
            # before casting it
            if (
                stage
                and not ModelVersionStage(mlflow_model_version.current_stage)
                == stage
            ):
                continue
            if created_after and not (
                mlflow_model_version.creation_timestamp
                >= created_after.timestamp()
            ):
                continue
            if created_before and not (
                mlflow_model_version.creation_timestamp
                <= created_before.timestamp()
            ):
                continue
            try:
                model_versions.append(
                    self._cast_mlflow_version_to_model_version(
                        mlflow_model_version=mlflow_model_version,
                    )
                )
            except (AttributeError, OSError) as e:
                # Sometimes, the Model Registry in MLflow can become unusable
                # due to failed version registration or misuse. In such rare
                # cases, it's best to suppress those versions that are not usable.
                logger.warning(
                    "Error encountered while loading MLflow model version "
                    f"`{mlflow_model_version.name}:{mlflow_model_version.version}`: {e}"
                )
            if count and len(model_versions) == count:
                return model_versions

        return model_versions

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from the MLflow model registry.

        This method loads the model version from the MLflow model registry
        and returns the model. The model is loaded using the `mlflow.pyfunc`
        module which takes care of loading the model from the model source
        URI for the right framework.

        Args:
            name: The name of the model.
            version: The version of the model.
            kwargs: Additional keyword arguments.

        Returns:
            The model version.

        Raises:
            KeyError: If the model version does not exist.
        """
        try:
            self.get_model_version(name=name, version=version)
        except KeyError:
            raise KeyError(
                f"Failed to load model version '{name}:{version}' from the "
                f"MLflow model registry: Model version does not exist."
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

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI artifact store.

        Args:
            model_version: The model version.

        Returns:
            The model URI artifact store.
        """
        artifact_store_path = (
            f"{Client().active_stack.artifact_store.path}/mlflow"
        )
        model_source_uri = model_version.model_source_uri.rsplit(":")[-1]
        return artifact_store_path + model_source_uri

    def _cast_mlflow_version_to_model_version(
        self,
        mlflow_model_version: MLflowModelVersion,
    ) -> RegistryModelVersion:
        """Cast an MLflow model version to a model version.

        Args:
            mlflow_model_version: The MLflow model version.

        Returns:
            The model version.
        """
        metadata = mlflow_model_version.tags or {}
        if mlflow_model_version.run_id:
            metadata["mlflow_run_id"] = mlflow_model_version.run_id
        if mlflow_model_version.run_link:
            metadata["mlflow_run_link"] = mlflow_model_version.run_link

        try:
            from mlflow.models import get_model_info

            model_library = (
                get_model_info(model_uri=mlflow_model_version.source)
                .flavors.get("python_function", {})
                .get("loader_module")
            )
        except ImportError:
            model_library = None
        return RegistryModelVersion(
            registered_model=RegisteredModel(name=mlflow_model_version.name),
            model_format=MLFLOW_MODEL_FORMAT,
            model_library=model_library,
            version=str(mlflow_model_version.version),
            created_at=datetime.fromtimestamp(
                int(mlflow_model_version.creation_timestamp) / 1e3
            ),
            stage=ModelVersionStage(mlflow_model_version.current_stage)
            if mlflow_model_version.current_stage
            else ModelVersionStage.NONE,
            description=mlflow_model_version.description,
            last_updated_at=datetime.fromtimestamp(
                int(mlflow_model_version.last_updated_timestamp) / 1e3
            ),
            metadata=ModelRegistryModelMetadata(**metadata),
            model_source_uri=mlflow_model_version.source,
        )
