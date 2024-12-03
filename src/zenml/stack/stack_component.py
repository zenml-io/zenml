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
"""Implementation of the ZenML Stack Component class."""

import json
from abc import ABC
from collections.abc import Mapping, Sequence
from datetime import datetime
from inspect import isclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from zenml.config.build_configuration import BuildConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements, StepRunResponse
from zenml.utils import (
    pydantic_utils,
    secret_utils,
    settings_utils,
    typing_utils,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import (
        ComponentResponse,
        PipelineDeploymentBase,
        PipelineDeploymentResponse,
    )
    from zenml.service_connectors.service_connector import ServiceConnector
    from zenml.stack import Stack, StackValidator

logger = get_logger(__name__)


class StackComponentConfig(BaseModel, ABC):
    """Base class for all ZenML stack component configs."""

    def __init__(
        self, warn_about_plain_text_secrets: bool = False, **kwargs: Any
    ) -> None:
        """Ensures that secret references don't clash with pydantic validation.

        StackComponents allow the specification of all their string attributes
        using secret references of the form `{{secret_name.key}}`. This however
        is only possible when the stack component does not perform any explicit
        validation of this attribute using pydantic validators. If this were
        the case, the validation would run on the secret reference and would
        fail or in the worst case, modify the secret reference and lead to
        unexpected behavior. This method ensures that no attributes that require
        custom pydantic validation are set as secret references.

        Args:
            warn_about_plain_text_secrets: If true, then warns about using
                plain-text secrets.
            **kwargs: Arguments to initialize this stack component.

        Raises:
            ValueError: If an attribute that requires custom pydantic validation
                is passed as a secret reference, or if the `name` attribute
                was passed as a secret reference.
        """
        for key, value in kwargs.items():
            try:
                field = self.__class__.model_fields[key]
            except KeyError:
                # Value for a private attribute or non-existing field, this
                # will fail during the upcoming pydantic validation
                continue

            if value is None:
                continue

            if not secret_utils.is_secret_reference(value):
                if (
                    secret_utils.is_secret_field(field)
                    and warn_about_plain_text_secrets
                ):
                    logger.warning(
                        "You specified a plain-text value for the sensitive "
                        f"attribute `{key}` for a `{self.__class__.__name__}` "
                        "stack component. This is currently only a warning, "
                        "but future versions of ZenML will require you to pass "
                        "in sensitive information as secrets. Check out the "
                        "documentation on how to configure your stack "
                        "components with secrets here: "
                        "https://docs.zenml.io/getting-started/deploying-zenml/secret-management"
                    )
                continue

            if pydantic_utils.has_validators(
                pydantic_class=self.__class__, field_name=key
            ):
                raise ValueError(
                    f"Passing the stack component attribute `{key}` as a "
                    "secret reference is not allowed as additional validation "
                    "is required for this attribute."
                )

        super().__init__(**kwargs)

    @property
    def required_secrets(self) -> Set[secret_utils.SecretReference]:
        """All required secrets for this stack component.

        Returns:
            The required secrets of this stack component.
        """
        return {
            secret_utils.parse_secret_reference(v)
            for v in self.model_dump().values()
            if secret_utils.is_secret_reference(v)
        }

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Concrete stack component configuration classes should override this
        method to return True if the stack component is running in a remote
        location, and it needs to access the ZenML database.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Examples:
          * Orchestrators that are running pipelines in the cloud or in a
          location other than the local host
          * Step Operators that are running steps in the cloud or in a location
          other than the local host

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return False

    @property
    def is_valid(self) -> bool:
        """Checks if the stack component configurations are valid.

        Concrete stack component configuration classes should override this
        method to return False if the stack component configurations are invalid.

        Returns:
            True if the stack component config is valid, False otherwise.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Concrete stack component configuration classes should override this
        method to return True if the stack component is relying on local
        resources or capabilities (e.g. local filesystem, local database or
        other services).

        Examples:
          * Artifact Stores that store artifacts in the local filesystem
          * Orchestrators that are connected to local orchestration runtime
          services (e.g. local Kubernetes clusters, Docker containers etc).

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    def __custom_getattribute__(self, key: str) -> Any:
        """Returns the (potentially resolved) attribute value for the given key.

        An attribute value may be either specified directly, or as a secret
        reference. In case of a secret reference, this method resolves the
        reference and returns the secret value instead.

        Args:
            key: The key for which to get the attribute value.

        Raises:
            KeyError: If the secret or secret key don't exist.

        Returns:
            The (potentially resolved) attribute value.
        """
        from zenml.client import Client

        value = super().__getattribute__(key)

        if not secret_utils.is_secret_reference(value):
            return value

        secret_ref = secret_utils.parse_secret_reference(value)

        # Try to resolve the secret using the secret store
        try:
            secret = Client().get_secret_by_name_and_scope(
                name=secret_ref.name,
            )
        except (KeyError, NotImplementedError):
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The secret "
                f"{secret_ref.name} does not exist."
            )

        if secret_ref.key not in secret.values:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`. "
                f"The secret {secret_ref.name} does not contain a value "
                f"for key {secret_ref.key}. Available keys: "
                f"{set(secret.values.keys())}."
            )

        return secret.secret_values[secret_ref.key]

    def _is_part_of_active_stack(self) -> bool:
        """Checks if this config belongs to a component in the active stack.

        Returns:
            True if this config belongs to a component in the active stack,
            False otherwise.
        """
        from zenml.client import Client

        for component in Client().active_stack.components.values():
            if component.config == self:
                return True
        return False

    if not TYPE_CHECKING:
        # When defining __getattribute__, mypy allows accessing non-existent
        # attributes without failing
        # (see https://github.com/python/mypy/issues/13319).
        __getattribute__ = __custom_getattribute__

    @model_validator(mode="before")
    @classmethod
    @pydantic_utils.before_validator_handler
    def _convert_json_strings(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Converts potential JSON strings.

        Args:
            data: The model data.

        Returns:
            The potentially converted data.

        Raises:
            ValueError: If any of the values is an invalid JSON string.
        """
        for key, field in cls.model_fields.items():
            if not field.annotation:
                continue

            value = data.get(key, None)

            if isinstance(value, str):
                if typing_utils.is_optional(field.annotation):
                    args = list(typing_utils.get_args(field.annotation))
                    if str in args:
                        # Don't do any type coercion in case str is in the
                        # possible types of the field
                        continue

                    # Remove `NoneType` from the arguments
                    NoneType = type(None)
                    if NoneType in args:
                        args.remove(NoneType)

                    # We just choose the first arg and match against this
                    annotation = args[0]
                else:
                    annotation = field.annotation

                if typing_utils.get_origin(annotation) in {
                    dict,
                    list,
                    Mapping,
                    Sequence,
                }:
                    try:
                        data[key] = json.loads(value)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Invalid json string '{value}'"
                        ) from e
                elif isclass(annotation) and issubclass(annotation, BaseModel):
                    data[key] = annotation.model_validate_json(
                        value
                    ).model_dump()

        return data

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="forbid",
    )


class StackComponent:
    """Abstract StackComponent class for all components of a ZenML stack."""

    def __init__(
        self,
        name: str,
        id: UUID,
        config: StackComponentConfig,
        flavor: str,
        type: StackComponentType,
        user: Optional[UUID],
        workspace: UUID,
        created: datetime,
        updated: datetime,
        labels: Optional[Dict[str, Any]] = None,
        connector_requirements: Optional[ServiceConnectorRequirements] = None,
        connector: Optional[UUID] = None,
        connector_resource_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ):
        """Initializes a StackComponent.

        Args:
            name: The name of the component.
            id: The unique ID of the component.
            config: The config of the component.
            flavor: The flavor of the component.
            type: The type of the component.
            user: The ID of the user who created the component.
            workspace: The ID of the workspace the component belongs to.
            created: The creation time of the component.
            updated: The last update time of the component.
            labels: The labels of the component.
            connector_requirements: The requirements for the connector.
            connector: The ID of a connector linked to the component.
            connector_resource_id: The custom resource ID to access through
                the connector.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If a secret reference is passed as name.
        """
        if secret_utils.is_secret_reference(name):
            raise ValueError(
                "Passing the `name` attribute of a stack component as a "
                "secret reference is not allowed."
            )

        self.id = id
        self.name = name
        self._config = config
        self.flavor = flavor
        self.type = type
        self.user = user
        self.workspace = workspace
        self.created = created
        self.updated = updated
        self.labels = labels
        self.connector_requirements = connector_requirements
        self.connector = connector
        self.connector_resource_id = connector_resource_id
        self._connector_instance: Optional[ServiceConnector] = None

    @classmethod
    def from_model(
        cls, component_model: "ComponentResponse"
    ) -> "StackComponent":
        """Creates a StackComponent from a ComponentModel.

        Args:
            component_model: The ComponentModel to create the StackComponent

        Returns:
            The created StackComponent.

        Raises:
            ImportError: If the flavor can't be imported.
        """
        flavor_model = component_model.flavor

        try:
            from zenml.stack import Flavor

            flavor = Flavor.from_model(flavor_model)
        except (ModuleNotFoundError, ImportError, NotImplementedError) as err:
            raise ImportError(
                f"Couldn't import flavor {flavor_model.name}: {err}"
            )

        configuration = flavor.config_class(**component_model.configuration)

        if component_model.user is not None:
            user_id = component_model.user.id
        else:
            user_id = None

        try:
            return flavor.implementation_class(
                user=user_id,
                workspace=component_model.workspace.id,
                name=component_model.name,
                id=component_model.id,
                config=configuration,
                labels=component_model.labels,
                flavor=component_model.flavor_name,
                type=component_model.type,
                created=component_model.created,
                updated=component_model.updated,
                connector_requirements=flavor.service_connector_requirements,
                connector=component_model.connector.id
                if component_model.connector
                else None,
                connector_resource_id=component_model.connector_resource_id,
            )
        except ImportError as e:
            from zenml.integrations.registry import integration_registry

            integration_requirements = " ".join(
                integration_registry.select_integration_requirements(
                    flavor_model.integration
                )
            )

            if integration_registry.is_installed(flavor_model.integration):
                raise ImportError(
                    f"{e}\n\n"
                    f"Something went wrong while trying to import from the "
                    f"`{flavor_model.integration}` integration. Please make "
                    "sure that all its requirements are installed properly by "
                    "reinstalling the integration either through our CLI: "
                    f"`zenml integration install {flavor_model.integration} "
                    "-y` or by manually installing its requirements: "
                    f"`pip install {integration_requirements}`. If the error"
                    "persists, please contact the ZenML team."
                ) from e
            else:
                raise ImportError(
                    f"{e}\n\n"
                    f"The `{flavor_model.integration}` integration that you "
                    "are trying to use is not installed in your current "
                    "environment. Please make sure that it is installed by "
                    "either using our CLI: `zenml integration install "
                    f"{flavor_model.integration}` or by manually installing "
                    f"its requirements: `pip install "
                    f"{integration_requirements}`"
                ) from e

    @property
    def config(self) -> StackComponentConfig:
        """Returns the configuration of the stack component.

        This should be overwritten by any subclasses that define custom configs
        to return the correct config class.

        Returns:
            The configuration of the stack component.
        """
        return self._config

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Class specifying available settings for this component.

        Returns:
            Optional settings class.
        """
        return None

    def get_settings(
        self,
        container: Union[
            "Step",
            "StepRunResponse",
            "StepRunInfo",
            "PipelineDeploymentBase",
            "PipelineDeploymentResponse",
        ],
    ) -> "BaseSettings":
        """Gets settings for this stack component.

        This will return `None` if the stack component doesn't specify a
        settings class or the container doesn't contain runtime
        options for this component.

        Args:
            container: The `Step`, `StepRunInfo` or `PipelineDeployment` from
                which to get the settings.

        Returns:
            Settings for this stack component.

        Raises:
            RuntimeError: If the stack component does not specify a settings
                class.
        """
        if not self.settings_class:
            raise RuntimeError(
                f"Unable to get settings for component {self} because this "
                "component does not have an associated settings class. "
                "Return a settings class from the `@settings_class` property "
                "and try again."
            )

        key = settings_utils.get_stack_component_setting_key(self)

        all_settings = (
            container.config.settings
            if isinstance(container, (Step, StepRunResponse, StepRunInfo))
            else container.pipeline_configuration.settings
        )

        if key in all_settings:
            return self.settings_class.model_validate(dict(all_settings[key]))
        else:
            return self.settings_class()

    def connector_has_expired(self) -> bool:
        """Checks whether the connector linked to this stack component has expired.

        Returns:
            Whether the connector linked to this stack component has expired, or isn't linked to a connector.
        """
        if self.connector is None:
            # The stack component isn't linked to a connector
            return False

        if self._connector_instance is None:
            return True

        return self._connector_instance.has_expired()

    def get_connector(self) -> Optional["ServiceConnector"]:
        """Returns the connector linked to this stack component.

        Returns:
            The connector linked to this stack component.

        Raises:
            RuntimeError: If the stack component does not specify connector
                requirements or if the connector linked to the component is not
                compatible or not found.
        """
        from zenml.client import Client

        if self.connector is None:
            return None

        if self._connector_instance is not None:
            # If the connector instance is still valid, return it. Otherwise,
            # we'll try to get a new one.
            if not self._connector_instance.has_expired():
                return self._connector_instance

        if self.connector_requirements is None:
            raise RuntimeError(
                f"Unable to get connector for component {self} because this "
                "component does not declare any connector requirements in its. "
                "flavor specification. Override the "
                "`service_connector_requirements` method in its flavor class "
                "to return a connector requirements specification and try "
                "again."
            )

        if self.connector_requirements.resource_id_attr is not None:
            # Check if an attribute is set in the component configuration
            resource_id = getattr(
                self.config, self.connector_requirements.resource_id_attr
            )
        else:
            # Otherwise, use the resource ID configured in the component
            resource_id = self.connector_resource_id

        client = Client()
        try:
            self._connector_instance = client.get_service_connector_client(
                name_id_or_prefix=self.connector,
                resource_type=self.connector_requirements.resource_type,
                resource_id=resource_id,
            )
        except KeyError:
            raise RuntimeError(
                f"The connector with ID {self.connector} linked "
                f"to the '{self.name}' {self.type} stack component could not "
                f"be found or is not accessible. Please verify that the "
                f"connector exists and that you have access to it."
            )
        except ValueError as e:
            raise RuntimeError(
                f"The connector with ID {self.connector} linked "
                f"to the '{self.name}' {self.type} stack component could not "
                f"be correctly configured: {e}."
            )
        except AuthorizationException as e:
            raise RuntimeError(
                f"The connector with ID {self.connector} linked "
                f"to the '{self.name}' {self.type} stack component could not "
                f"be accessed due to an authorization error: {e}. Please "
                f"verify that you have access to the connector and try again."
            )

        return self._connector_instance

    @property
    def log_file(self) -> Optional[str]:
        """Optional path to a log file for the stack component.

        Returns:
            Optional path to a log file for the stack component.
        """
        # TODO [ENG-136]: Add support for multiple log files for a stack
        #  component. E.g. let each component return a generator that yields
        #  logs instead of specifying a single file path.
        return None

    @property
    def requirements(self) -> Set[str]:
        """Set of PyPI requirements for the component.

        Returns:
            A set of PyPI requirements for the component.
        """
        from zenml.integrations.utils import get_requirements_for_module

        return set(get_requirements_for_module(self.__module__))

    @property
    def apt_packages(self) -> List[str]:
        """List of APT package requirements for the component.

        Returns:
            A list of APT package requirements for the component.
        """
        from zenml.integrations.utils import get_integration_for_module

        integration = get_integration_for_module(self.__module__)
        return integration.APT_PACKAGES if integration else []

    @property
    def local_path(self) -> Optional[str]:
        """Path to a local directory to store persistent information.

        This property should only be implemented by components that need to
        store persistent information in a directory on the local machine and
        also need that information to be available during pipeline runs.

        IMPORTANT: the path returned by this property must always be a path
        that is relative to the ZenML local store's directory. The local
        orchestrators rely on this convention to correctly mount the
        local folders in the containers. This is an example of a valid
        path:

        ```python
        from zenml.config.global_config import GlobalConfiguration

        ...

        @property
        def local_path(self) -> Optional[str]:

            return os.path.join(
                GlobalConfiguration().local_stores_path,
                str(self.uuid),
            )
        ```

        Returns:
            A path to a local directory used by the component to store
            persistent information.
        """
        return None

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        return []

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
    ) -> None:
        """Prepares deploying the pipeline.

        This method gets called immediately before a pipeline is deployed.
        Subclasses should override it if they require runtime configuration
        options or if they need to run code before the pipeline deployment.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        return {}

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Prepares running a step.

        Args:
            info: Info about the step that will be executed.
        """

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        return {}

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Cleans up resources after the step run is finished.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed.
        """

    @property
    def post_registration_message(self) -> Optional[str]:
        """Optional message printed after the stack component is registered.

        Returns:
            An optional message.
        """
        return None

    @property
    def validator(self) -> Optional["StackValidator"]:
        """The optional validator of the stack component.

        This validator will be called each time a stack with the stack
        component is initialized. Subclasses should override this property
        and return a `StackValidator` that makes sure they're not included in
        any stack that they're not compatible with.

        Returns:
            An optional `StackValidator` instance.
        """
        return None

    def cleanup(self) -> None:
        """Cleans up the component after it has been used."""
        pass

    def __repr__(self) -> str:
        """String representation of the stack component.

        Returns:
            A string representation of the stack component.
        """
        attribute_representation = ", ".join(
            f"{key}={value}" for key, value in self.config.model_dump().items()
        )
        return (
            f"{self.__class__.__qualname__}(type={self.type}, "
            f"flavor={self.flavor}, {attribute_representation})"
        )

    def __str__(self) -> str:
        """String representation of the stack component.

        Returns:
            A string representation of the stack component.
        """
        return self.__repr__()
