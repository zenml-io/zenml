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

import mlflow.pyfunc
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

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

        Returns:
            The MLFlowClient.
        """
        if not self._client:
            # TODO: if this sounds like a hacky way how can we do this better?
            experiment_tracker = Client().active_stack.experiment_tracker
            if not isinstance(experiment_tracker, MLFlowExperimentTracker):
                raise get_missing_mlflow_experiment_tracker_error()
            experiment_tracker.configure_mlflow()
            self._client = MlflowClient()
        return self._client

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains an mlflow expirement tracker.

        Returns:
            A StackValidator instance.
        """

        def _validate_stack_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that the expirement tracker is an mlflow expirement tracker.

            Args:
                stack: The stack to validate.

            Returns:
                A tuple of (is_valid, error_message).
            """
            # Validate that the expirement tracker is an mlflow expirementb tracker.
            expirement_tracker = stack.experiment_tracker
            assert expirement_tracker is not None
            if expirement_tracker.flavor != "mlflow":
                return False, (
                    "The MLFlow model registry requires a MLFlow expirement "
                    "tracker. You should register a MLFlow expirement "
                    "tracker to the stack using the following command: "
                    "`zenml stack register expirement_tracker ..."
                )
            expirement_tracker
            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.EXPERIMENT_TRACKER,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelRegistration:
        """Register a model to the MLFlow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            tags: The tags of the model.

        Raises:
            MlflowException: If the model already exists.

        Returns:
            The registered model.
        """
        try:
            registered_model = self.mlflow_client.create_registered_model(
                name=name,
                description=description,
                tags=tags,
            )
        except MlflowException as e:
            raise e
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
            name: The name of the model.

        Raises:
            MlflowException: If the model does not exist.
        """
        try:
            self.mlflow_client.delete_registered_model(
                name=name,
            )
        except MlflowException as e:
            raise e

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelRegistration:
        """Update a model in the MLFlow model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            tags: The tags of the model.

        Raises:
            MlflowException: If the model does not exist.

        Returns:
            The updated model.
        """
        # Update the registered model description.
        if description:
            try:
                self.mlflow_client.update_registered_model(
                    name=name,
                    description=description,
                )
            except MlflowException as e:
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
            MlflowException: If the model does not exist.
        """
        # Get the registered model.
        try:
            registered_model = self.mlflow_client.get_registered_model(
                name=name,
            )
        except MlflowException as e:
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
            name: The name of the model.
            tags: A dictionary of tags to filter the models by.

        Returns:
            A list of models.
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

    def register_model_version(
        self,
        model_version: ModelVersion,
        **kwargs: Any,
    ) -> ModelVersion:
        """Register a model version to the MLFlow model registry.

        Args:
            model_version: The model to register.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            MlflowException: If the registered model does not exist.

        Returns:
            The registered model version.
        """
        if not self._check_model_exists(model_version.model_registration.name):
            logger.info(
                f"Model '{model_version.model_registration.name}' does not exist. Creating model."
            )
            self.register_model(
                name=model_version.model_registration.name,
                description=model_version.model_registration.description,
                tags=model_version.model_registration.tags,
            )
        try:
            registered_model_version = self.mlflow_client.create_model_version(
                name=model_version.model_registration.name,
                source=model_version.model_source_uri,
                run_id=model_version.model_registry_metadata.get(
                    "mlflow_run_id"
                )
                or None,
                run_link=model_version.model_registry_metadata.get(
                    "mlflow_run_link"
                ),
                description=model_version.description,
                tags=model_version.tags,
            )
        except MlflowException as e:
            raise e

        # Return the registered model version.
        return ModelVersion(
            model_registration=ModelRegistration(
                name=registered_model_version.name,
            ),
            model_source_uri=registered_model_version.source,
            model_registry_metadata={
                "mlflow_run_id": registered_model_version.run_id or "",
                "mlflow_run_link": registered_model_version.run_link or "",
            },
            version=registered_model_version.version,
            description=registered_model_version.description,
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
            name: The name of the model.
            version: The version of the model.

        Raises:
            MlflowException: If the model version does not exist.
        """
        if not self._check_model_version_exists(name, version):
            raise KeyError(
                f"The model version '{name}:{version}' does not exist."
            )
        try:
            self.mlflow_client.delete_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            raise e

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        stage: Optional[str] = None,
    ) -> ModelVersion:
        """Update a model version in the MLFlow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            description: The description of the model.
            tags: A dictionary of tags to filter the models by.
            stage: The stage of the model.

        Raises:
            MlflowException: If the model version does not exist.

        Returns:
            The updated model version.
        """
        if not self._check_model_version_exists(name, version):
            raise KeyError(
                f"The model version '{name}:{version}' does not exist."
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
                raise e
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
                raise e
        # Update the model stage.
        if stage:
            try:
                self.mlflow_client.transition_model_version_stage(
                    name=name,
                    version=version,
                    stage=stage,
                )
            except MlflowException as e:
                raise e
        return self.get_model_version(name, version)

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> ModelVersion:
        """Get a model version from the MLFlow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            MlflowException: If the model version does not exist.

        Returns:
            The model version.
        """
        try:
            mlflow_model_version = self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            raise e

        return ModelVersion(
            model_registration=ModelRegistration(
                name=mlflow_model_version.name
            ),
            version=mlflow_model_version.version,
            created_at=str(mlflow_model_version.creation_timestamp),
            current_stage=mlflow_model_version.current_stage,
            description=mlflow_model_version.description,
            last_updated_at=str(mlflow_model_version.last_updated_timestamp),
            model_registry_metadata={
                "mlflow_run_id": mlflow_model_version.run_id or "",
                "mlflow_run_link": mlflow_model_version.run_link or "",
            },
            model_source_uri=mlflow_model_version.source,
            tags=mlflow_model_version.tags,
        )

    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[ModelVersion]:
        """List model versions from the MLFlow model registry.

        Args:
            name: The name of the model.
            model_source_uri: The model source URI.
            tags: The tags to filter by.
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
            ModelVersion(
                model_registration=ModelRegistration(
                    name=mlflow_model_version.name
                ),
                version=mlflow_model_version.version,
                created_at=str(mlflow_model_version.creation_timestamp),
                current_stage=mlflow_model_version.current_stage,
                description=mlflow_model_version.description,
                last_updated_at=str(
                    mlflow_model_version.last_updated_timestamp
                ),
                model_registry_metadata={
                    "mlflow_run_id": mlflow_model_version.run_id or "",
                    "mlflow_run_link": mlflow_model_version.run_link or "",
                },
                model_source_uri=mlflow_model_version.source,
                tags=mlflow_model_version.tags,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def get_latest_model_versions(
        self,
        name: Optional[str] = None,
        stages: Optional[List[str]] = None,
    ) -> List[ModelVersion]:
        """Get the latest model versions from the MLFlow model registry.

        Args:
            name: The name of the model.
            stages: The stages to fsilter by.

        Returns:
            The latest model versions or None if no model versions exist.
        """
        # Get the latest model versions.
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
                current_stage=mlflow_model_version.current_stage,
                description=mlflow_model_version.description,
                last_updated_at=str(
                    mlflow_model_version.last_updated_timestamp
                ),
                model_registry_metadata={
                    "mlflow_run_id": mlflow_model_version.run_id or "",
                    "mlflow_run_link": mlflow_model_version.run_link or "",
                },
                model_source_uri=mlflow_model_version.source,
                tags=mlflow_model_version.tags,
            )
            for mlflow_model_version in mlflow_model_versions
        ]

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from the MLFlow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            kwargs: Additional keyword arguments.

        Returns:
            The model.
        """
        # Load the model.
        model = mlflow.pyfunc.load_model(model_uri=f"models:/{name}/{version}")

        # Return the model.
        return model

    def _check_model_exists(
        self,
        name: str,
    ) -> bool:
        """Check if a model exists in the MLFlow model registry.

        Args:
            name: The name of the model.

        Returns:
            True if the model exists, False otherwise.
        """
        try:
            self.mlflow_client.get_registered_model(name=name)
        except MlflowException:
            return False
        return True

    def _check_model_version_exists(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Check if a model version exists in the MLFlow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            True if the model version exists, False otherwise.
        """
        try:
            self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
        except MlflowException:
            return False
        return True
