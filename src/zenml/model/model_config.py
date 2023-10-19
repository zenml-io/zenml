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
"""ModelConfig user facing interface to pass into pipeline or step."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel, root_validator

from zenml.constants import RUNNING_MODEL_VERSION
from zenml.enums import ExecutionStatus, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models.model_models import (
        ModelResponseModel,
        ModelVersionResponseModel,
    )

logger = get_logger(__name__)


class ModelConfig(BaseModel):
    """ModelConfig class to pass into pipeline or step to set it into a model context.

    name: The name of the model.
    license: The license under which the model is created.
    description: The description of the model.
    audience: The target audience of the model.
    use_cases: The use cases of the model.
    limitations: The known limitations of the model.
    trade_offs: The tradeoffs of the model.
    ethics: The ethical implications of the model.
    tags: Tags associated with the model.
    version: The model version name, number or stage is optional and points model context
        to a specific version/stage. If skipped and `create_new_model_version` is False -
        latest model version will be used.
    version_description: The description of the model version.
    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    delete_new_version_on_failure: Whether to delete failed runs with new versions for later recovery from it.
    """

    name: str
    license: Optional[str]
    description: Optional[str]
    audience: Optional[str]
    use_cases: Optional[str]
    limitations: Optional[str]
    trade_offs: Optional[str]
    ethics: Optional[str]
    tags: Optional[List[str]]
    version: Optional[Union[ModelStages, int, str]]
    version_description: Optional[str]
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    delete_new_version_on_failure: bool = True

    suppress_class_validation_warnings: bool = False

    class Config:
        """Config class."""

        smart_union = True

    @root_validator(pre=True)
    def _root_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all in one.

        Args:
            values: Dict of values.

        Returns:
            Dict of validated values.

        Raises:
            ValueError: If validation failed on one of the checks.
        """
        create_new_model_version = values.get(
            "create_new_model_version", False
        )
        suppress_class_validation_warnings = values.get(
            "suppress_class_validation_warnings", False
        )
        version = values.get("version", None)

        if create_new_model_version:
            misuse_message = (
                "`version` set to {set} cannot be used with `create_new_model_version`."
                "You can leave it default or set to a non-stage and non-numeric string.\n"
                "Examples:\n"
                " - `version` set to 1 or '1' is interpreted as a version number\n"
                " - `version` set to 'production' is interpreted as a stage\n"
                " - `version` set to 'my_first_version_in_2023' is a valid version to be created\n"
                " - `version` set to 'My Second Version!' is a valid version to be created\n"
            )
            if isinstance(version, ModelStages) or version in [
                stage.value for stage in ModelStages
            ]:
                raise ValueError(
                    misuse_message.format(set="a `ModelStages` instance")
                )
            if str(version).isnumeric():
                raise ValueError(misuse_message.format(set="a numeric value"))
            if version is None:
                if not suppress_class_validation_warnings:
                    logger.info(
                        "Creation of new model version was requested, but no version name was explicitly provided. "
                        f"Setting `version` to `{RUNNING_MODEL_VERSION}`."
                    )
                values["version"] = RUNNING_MODEL_VERSION
        if (
            version in [stage.value for stage in ModelStages]
            and not suppress_class_validation_warnings
        ):
            logger.info(
                f"`version` `{version}` matches one of the possible `ModelStages` and will be fetched using stage."
            )
        if str(version).isnumeric() and not suppress_class_validation_warnings:
            logger.info(
                f"`version` `{version}` is numeric and will be fetched using version number."
            )
        values["suppress_class_validation_warnings"] = True
        return values

    def _validate_config_in_runtime(self) -> None:
        """Validate that config doesn't conflict with runtime environment.

        Raises:
            RuntimeError: If recovery not requested, but model version already exists.
            RuntimeError: If there is unfinished pipeline run for requested new model version.
        """
        try:
            model_version = self._get_model_version()
            if self.create_new_model_version:
                for run_name, run in model_version.pipeline_runs.items():
                    if run.status == ExecutionStatus.RUNNING:
                        raise RuntimeError(
                            f"New model version was requested, but pipeline run `{run_name}` "
                            f"is still running with version `{model_version.name}`."
                        )

                if self.delete_new_version_on_failure:
                    raise RuntimeError(
                        f"Cannot create version `{self.version}` "
                        f"for model `{self.name}` since it already exists"
                    )
        except KeyError:
            self.get_or_create_model_version()

    def get_or_create_model(self) -> "ModelResponseModel":
        """This method should get or create a model from Model Control Plane.

        New model is created implicitly, if missing, otherwise fetched.

        Returns:
            The model based on configuration.
        """
        from zenml.client import Client
        from zenml.models.model_models import ModelRequestModel

        zenml_client = Client()
        try:
            model = zenml_client.get_model(model_name_or_id=self.name)
        except KeyError:
            model_request = ModelRequestModel(
                name=self.name,
                license=self.license,
                description=self.description,
                audience=self.audience,
                use_cases=self.use_cases,
                limitations=self.limitations,
                trade_offs=self.trade_offs,
                ethics=self.ethics,
                tags=self.tags,
                user=zenml_client.active_user.id,
                workspace=zenml_client.active_workspace.id,
            )
            model_request = ModelRequestModel.parse_obj(model_request)
            try:
                model = zenml_client.create_model(model=model_request)
                logger.info(f"New model `{self.name}` was created implicitly.")
            except EntityExistsError:
                # this is backup logic, if model was created somehow in between get and create calls
                model = zenml_client.get_model(model_name_or_id=self.name)

        return model

    def _create_model_version(
        self, model: "ModelResponseModel"
    ) -> "ModelVersionResponseModel":
        """This method creates a model version for Model Control Plane.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        from zenml.client import Client
        from zenml.models.model_models import ModelVersionRequestModel

        zenml_client = Client()
        model_version_request = ModelVersionRequestModel(
            user=zenml_client.active_user.id,
            workspace=zenml_client.active_workspace.id,
            name=self.version,
            description=self.version_description,
            model=model.id,
        )
        mv_request = ModelVersionRequestModel.parse_obj(model_version_request)
        try:
            mv = zenml_client.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_number_or_id=self.version,
            )
            model_version = mv
        except KeyError:
            model_version = zenml_client.create_model_version(
                model_version=mv_request
            )
            logger.info(f"New model version `{self.version}` was created.")

        return model_version

    def _get_model_version(self) -> "ModelVersionResponseModel":
        """This method gets a model version from Model Control Plane.

        Returns:
            The model version based on configuration.
        """
        from zenml.client import Client

        zenml_client = Client()
        if self.version is None:
            # raise if not found
            model_version = zenml_client.get_model_version(
                model_name_or_id=self.name
            )
        else:
            # by version name or stage or number
            # raise if not found
            model_version = zenml_client.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_number_or_id=self.version,
            )
        return model_version

    def get_or_create_model_version(self) -> "ModelVersionResponseModel":
        """This method should get or create a model and a model version from Model Control Plane.

        A new model is created implicitly if missing, otherwise existing model is fetched. Model
        name is controlled by the `name` parameter.

        Model Version returned by this method is resolved based on model configuration:
        - If there is an existing model version leftover from the previous failed run with
        `delete_new_version_on_failure` is set to False and `create_new_model_version` is True,
        leftover model version will be reused.
        - Otherwise if `create_new_model_version` is True, a new model version is created.
        - If `create_new_model_version` is False a model version will be fetched based on the version:
            - If `version` is not set, the latest model version will be fetched.
            - If `version` is set to a string, the model version with the matching version will be fetched.
            - If `version` is set to a `ModelStage`, the model version with the matching stage will be fetched.

        Returns:
            The model version based on configuration.
        """
        model = self.get_or_create_model()
        if self.create_new_model_version:
            mv = self._create_model_version(model)
        else:
            mv = self._get_model_version()
        return mv

    def _merge(self, model_config: "ModelConfig") -> None:
        self.license = self.license or model_config.license
        self.description = self.description or model_config.description
        self.audience = self.audience or model_config.audience
        self.use_cases = self.use_cases or model_config.use_cases
        self.limitations = self.limitations or model_config.limitations
        self.trade_offs = self.trade_offs or model_config.trade_offs
        self.ethics = self.ethics or model_config.ethics
        if model_config.tags is not None:
            self.tags = list(
                {t for t in self.tags or []}.union(set(model_config.tags))
            )

        self.delete_new_version_on_failure &= (
            model_config.delete_new_version_on_failure
        )
