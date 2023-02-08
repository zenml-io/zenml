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

from zenml.enums import StackComponentType
from zenml.integrations.mlflow.flavors.mlflow_model_registry_flavor import (
    MLFlowModelRegistryConfig,
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

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.EXPERIMENT_TRACKER,
            },
            custom_validation_function=_validate_stack_requirements,
        )

    def register_model(self, registered_model: ModelRegistration) -> None:
        """Register a model to the MLFlow model registry.

        Args:
            registered_model: The model to register.
        """
        try:
            registered_model = self.mlflow_client.create_registered_model(
                name=registered_model.name,
                description=registered_model.description,
                tags=registered_model.tags,
            )
        except MlflowException as e:
            logger.error(f"Error occurred while registering the model: \n{e}")
            raise e

    def delete_model(self, registered_model: ModelRegistration) -> None:
        """Delete a model from the MLFlow model registry.

        Args:
            registered_model: The model to delete.
        """
        try:
            self.mlflow_client.delete_registered_model(
                name=registered_model.name,
            )
        except MlflowException as e:
            logger.error(f"Error occurred while deleting the model: \n{e}")
            raise e

    def update_model(self, registered_model: ModelRegistration) -> None:
        """Update a model in the MLFlow model registry.

        Args:
            registered_model: The model to update.
        """
        # TODO: Support updating the registered model tags.
        try:
            self.mlflow_client.update_registered_model(
                name=registered_model.name,
                description=registered_model.description,
            )
        except MlflowException as e:
            logger.error(f"Error occurred while updating the model: \n{e}")
            raise e

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
        filter_string = ""
        if name:
            filter_string += f"name='{name}'"
        if tags:
            for tag, value in tags.items():
                if filter_string:
                    filter_string += " AND "
                filter_string += f"tags.{tag}='{value}'"
        try:
            registered_models = self.mlflow_client.search_registered_models(
                filter_string=filter_string,
                max_results=100,
            )
        except MlflowException as e:
            logger.error(f"Error occurred while listing the models: \n{e}")
            raise e

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
        """
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
            logger.error(
                f"Error occurred while registering the model version: \n{e}"
            )
            raise e

        return ModelVersion(
            model_registration=ModelRegistration(
                name=registered_model_version.name,
            ),
            model_source_uri=registered_model_version.source,
            # model_registry_metadata={
            #    "mlflow_run_id": registered_model_version.run_id,
            #    "mlflow_run_link": registered_model_version.run_link,
            # },
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
        """
        try:
            self.mlflow_client.delete_model_version(
                name=name,
                version=version,
            )
        except MlflowException as e:
            logger.error(
                f"Error occurred while deleting the model version: \n{e}"
            )
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
        """
        # TODO: Support updating the model version tags.
        # TODO: Support updating the model version stage.
        try:
            updated_model_version = self.mlflow_client.update_model_version(
                name=name,
                version=version,
                description=description,
            )
        except MlflowException as e:
            logger.error(
                f"Error occurred while updating the model version: \n{e}"
            )
            raise e
        return ModelVersion(
            model_registration=ModelRegistration(
                name=updated_model_version.name
            ),
            version=updated_model_version.version,
            model_source_uri=updated_model_version.source,
            created_at=str(updated_model_version.creation_timestamp),
            current_stage=updated_model_version.current_stage,
            description=updated_model_version.description,
            last_updated_at=str(updated_model_version.last_updated_timestamp),
            model_registry_metadata={
                "mlflow_run_id": updated_model_version.run_id,
                "mlflow_run_link": updated_model_version.run_link,
            },
            tags=updated_model_version.tags,
        )

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> ModelVersion:
        """Get a model version from the MLFlow model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            The model version.
        """
        try:
            mlflow_model_version = self.mlflow_client.get_model_version(
                name=name,
                version=version,
            )
            return ModelVersion(
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
                    "mlflow_run_id": mlflow_model_version.run_id,
                    "mlflow_run_link": mlflow_model_version.run_link,
                },
                model_source_uri=mlflow_model_version.source,
                tags=mlflow_model_version.tags,
            )
        except MlflowException as e:
            logger.error(
                f"Error occurred while getting the model version: \n{e}"
            )
            raise e

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
        try:
            mlflow_model_versions = self.mlflow_client.search_model_versions(
                filter_string=filter_string,
            )
        except MlflowException as e:
            logger.error(
                f"Error occurred while listing the model versions: \n{e}"
            )
            raise e
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
                    "mlflow_run_id": mlflow_model_version.run_id,
                    "mlflow_run_link": mlflow_model_version.run_link,
                },
                model_source_uri=mlflow_model_version.source,
                tags=mlflow_model_version.tags,
            )
            for mlflow_model_version in mlflow_model_versions
        ]
