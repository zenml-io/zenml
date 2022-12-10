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
from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Set, Type, Union
from uuid import UUID

from pydantic import BaseModel, Extra

from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models import ComponentResponseModel
from zenml.utils import secret_utils, settings_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import Stack, StackValidator


logger = get_logger(__name__)


class StackComponentConfig(BaseModel, ABC):
    """Base class for all ZenML stack component configs."""

    def __init__(self, **kwargs: Any) -> None:
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
            **kwargs: Arguments to initialize this stack component.

        Raises:
            ValueError: If an attribute that requires custom pydantic validation
                is passed as a secret reference, or if the `name` attribute
                was passed as a secret reference.
        """
        for key, value in kwargs.items():
            try:
                field = self.__class__.__fields__[key]
            except KeyError:
                # Value for a private attribute or non-existing field, this
                # will fail during the upcoming pydantic validation
                continue

            if value is None:
                continue

            if not secret_utils.is_secret_reference(value):
                if secret_utils.is_secret_field(field):
                    logger.warning(
                        "You specified a plain-text value for the sensitive "
                        f"attribute `{key}` for a `{self.__class__.__name__}` "
                        "stack component. This is currently only a warning, "
                        "but future versions of ZenML will require you to pass "
                        "in sensitive information as secrets. Check out the "
                        "documentation on how to configure your stack "
                        "components with secrets here: "
                        "https://docs.zenml.io/advanced-guide/practical/secrets-management"
                    )
                continue

            requires_validation = field.pre_validators or field.post_validators
            if requires_validation:
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
            for v in self.dict().values()
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
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Concrete stack component configuration classes should override this
        method to return True if the stack component is relying on local
        resources or capabilities (e.g. local filesystem, local database or
        other services).

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

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
            RuntimeError: If the stack component is not part of the active
                stack, or the active stack is missing a secrets manager.
            KeyError: If the secret or secret key don't exist.

        Returns:
            The (potentially resolved) attribute value.
        """
        value = super().__getattribute__(key)

        if not secret_utils.is_secret_reference(value):
            return value

        # A stack component can be part of many stacks, and currently a
        # secrets manager is associated with a stack. This means we're
        # not able to identify the 'correct' secrets manager that the user
        # wanted to resolve the secrets in a general way. We therefore
        # limit secret resolving to components of the active stack.
        if not self._is_part_of_active_stack():
            raise RuntimeError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The stack component is not "
                "part of the active stack and therefore can't have it's "
                "secret references resolved. If you want to access attributes "
                "of this stack component which reference secrets, set a stack "
                "which includes both this component and a secrets manager as "
                "your active stack: `zenml stack set <STACK_NAME>`."
            )

        from zenml.client import Client

        secrets_manager = Client().active_stack.secrets_manager
        if not secrets_manager:
            raise RuntimeError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The active stack does not "
                "have a secrets manager."
            )

        secret_ref = secret_utils.parse_secret_reference(value)
        try:
            secret = secrets_manager.get_secret(secret_ref.name)
        except KeyError:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The secret "
                f"{secret_ref.name} does not exist."
            )

        try:
            secret_value = secret.content[secret_ref.key]
        except KeyError:
            raise KeyError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The secret "
                f"{secret_ref.name} does not contain a value for key "
                f"{secret_ref.key}. Available keys: {set(secret.content)}."
            )

        return str(secret_value)

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

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
        # prevent extra attributes during model initialization
        extra = Extra.forbid


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
        project: UUID,
        created: datetime,
        updated: datetime,
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
            project: The ID of the project the component belongs to.
            created: The creation time of the component.
            updated: The last update time of the component.
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
        self.project = project
        self.created = created
        self.updated = updated

    @classmethod
    def from_model(
        cls, component_model: "ComponentResponseModel"
    ) -> "StackComponent":
        """Creates a StackComponent from a ComponentModel.

        Args:
            component_model: The ComponentModel to create the StackComponent

        Returns:
            The created StackComponent.

        Raises:
            ImportError: If the flavor can't be imported.
        """
        from zenml.client import Client

        flavor_model = Client().get_flavor_by_name_and_type(
            name=component_model.flavor,
            component_type=component_model.type,
        )

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

        return flavor.implementation_class(
            user=user_id,
            project=component_model.project.id,
            name=component_model.name,
            id=component_model.id,
            config=configuration,
            flavor=component_model.flavor,
            type=component_model.type,
            created=component_model.created,
            updated=component_model.updated,
        )

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
        self, container: Union["Step", "StepRunInfo", "PipelineDeployment"]
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
            if isinstance(container, (Step, StepRunInfo))
            else container.pipeline.settings
        )

        if key in all_settings:
            return self.settings_class.parse_obj(all_settings[key])
        else:
            return self.settings_class()

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

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
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

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Prepares running a step.

        Args:
            info: Info about the step that will be executed.
        """

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

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run.

        Returns:
            True if the component provisioned resources to run.
        """
        return True

    @property
    def is_running(self) -> bool:
        """If the component is running.

        Returns:
            True if the component is running.
        """
        return True

    @property
    def is_suspended(self) -> bool:
        """If the component is suspended.

        Returns:
            True if the component is suspended.
        """
        return not self.is_running

    def provision(self) -> None:
        """Provisions resources to run the component.

        Raises:
            NotImplementedError: If the component does not implement this
                method.
        """
        raise NotImplementedError(
            f"Provisioning resources not implemented for {self}."
        )

    def deprovision(self) -> None:
        """Deprovisions all resources of the component.

        Raises:
            NotImplementedError: If the component does not implement this
                method.
        """
        raise NotImplementedError(
            f"Deprovisioning resource not implemented for {self}."
        )

    def resume(self) -> None:
        """Resumes the provisioned resources of the component.

        Raises:
            NotImplementedError: If the component does not implement this
                method.
        """
        raise NotImplementedError(
            f"Resuming provisioned resources not implemented for {self}."
        )

    def suspend(self) -> None:
        """Suspends the provisioned resources of the component.

        Raises:
            NotImplementedError: If the component does not implement this
                method.
        """
        raise NotImplementedError(
            f"Suspending provisioned resources not implemented for {self}."
        )

    def __repr__(self) -> str:
        """String representation of the stack component.

        Returns:
            A string representation of the stack component.
        """
        attribute_representation = ", ".join(
            f"{key}={value}" for key, value in self.config.dict().items()
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
