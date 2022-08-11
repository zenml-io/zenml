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

import textwrap
from abc import ABC
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Extra, Field, root_validator

from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger
from zenml.utils import secret_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack, StackValidator

logger = get_logger(__name__)


def uuid_factory() -> UUID:
    """Generates a UUID whose hex string does not start with a '0'.

    Returns:
        A UUID whose hex string does not start with a '0'.
    """
    # TODO [MEDIUM]: This is a replica of the fix which is applied
    #   to the zen_store.sql_zen_store.SQLZenStore. Since the UUID for
    #   stack components get created upon the creation of the
    #   pydantic instance, the same logic must apply here in order to
    #   save it within the ZenStore.
    # SQLModel crashes when a UUID hex string starts with '0'
    # (see: https://github.com/tiangolo/sqlmodel/issues/25)
    uuid = uuid4()
    while uuid.hex[0] == "0":
        uuid = uuid4()
    return uuid


class StackComponent(BaseModel, ABC):
    """Abstract StackComponent class for all components of a ZenML stack.

    Attributes:
        name: The name of the component.
        uuid: Unique identifier of the component.
    """

    name: str
    uuid: UUID = Field(default_factory=uuid_factory)

    # Class Configuration
    TYPE: ClassVar[StackComponentType]
    FLAVOR: ClassVar[str]

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
                        "in senstive information as secrets. Check out the "
                        "documentation on how to configure your stack "
                        "components with secrets here: "
                        "https://docs.zenml.io/developer-guide/advanced-usage/secret-references"
                    )
                continue

            if key == "name":
                raise ValueError(
                    "Passing the `name` attribute of a stack component as a "
                    "secret reference is not allowed."
                )

            requires_validation = field.pre_validators or field.post_validators
            if requires_validation:
                raise ValueError(
                    f"Passing the stack component attribute `{key}` as a "
                    "secret reference is not allowed as additional validation "
                    "is required for this attribute."
                )

        super().__init__(**kwargs)

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

        from zenml.repository import Repository

        stack = Repository().active_stack

        # A stack component can be part of many stacks, and currently a
        # secrets manager is associated with a stack. This means we're
        # not able to identify the 'correct' secrets manager that the user
        # wanted to resolve the secrets in a general way. We therefore
        # limit secret resolving to components of the active stack.
        component = stack.components.get(self.TYPE, None)
        if not component or component.uuid != self.uuid:
            raise RuntimeError(
                f"Failed to resolve secret reference for attribute {key} "
                f"of stack component `{self}`: The stack component is not "
                "part of the active stack and therefore can't have it's "
                "secret references resolved. If you want to access attributes "
                "of this stack component which reference secrets, set a stack "
                "which includes both this component and a secrets manager as "
                "your active stack: `zenml stack set <STACK_NAME>`."
            )

        secrets_manager = Repository().active_stack.secrets_manager
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

    if not TYPE_CHECKING:
        # When defining __getattribute__, mypy allows accessing non-existent
        # attributes without failing
        # (see https://github.com/python/mypy/issues/13319).
        __getattribute__ = __custom_getattribute__

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
    def runtime_options(self) -> Dict[str, Any]:
        """Runtime options that are available to configure this component.

        The items of the dictionary should map option names (which can be used
        to configure the option in the `RuntimeConfiguration`) to default
        values for the option (or `None` if there is no default value).

        Returns:
            A dictionary of runtime options.
        """
        return {}

    @property
    def requirements(self) -> Set[str]:
        """Set of PyPI requirements for the component.

        Returns:
            A set of PyPI requirements for the component.
        """
        from zenml.integrations.utils import get_requirements_for_module

        return set(get_requirements_for_module(self.__module__))

    @property
    def local_path(self) -> Optional[str]:
        """Path to a local directory used by the component to store persistent information.

        This property should only be implemented by components that need to
        store persistent information in a directory on the local machine and
        also need that information to be available during pipeline runs.

        IMPORTANT: the path returned by this property must always be a path
        that is relative to the ZenML global config directory. The local
        Kubeflow orchestrator relies on this convention to correctly mount the
        local folders in the Kubeflow containers. This is an example of a valid
        path:

        ```python
        from zenml.utils.io_utils import get_global_config_directory
        from zenml.constants import LOCAL_STORES_DIRECTORY_NAME

        ...

        @property
        def local_path(self) -> Optional[str]:

            return os.path.join(
                get_global_config_directory(),
                LOCAL_STORES_DIRECTORY_NAME,
                str(uuid),
            )
        ```

        Returns:
            A path to a local directory used by the component to store
            persistent information.
        """
        return None

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Prepares deploying the pipeline.

        This method gets called immediately before a pipeline is deployed.
        Subclasses should override it if they require runtime configuration
        options or if they need to run code before the pipeline deployment.

        Args:
            pipeline: The pipeline that will be deployed.
            stack: The stack on which the pipeline will be deployed.
            runtime_configuration: Contains all the runtime configuration
                options specified for the pipeline run.
        """

    def prepare_pipeline_run(self) -> None:
        """Prepares running the pipeline."""

    def cleanup_pipeline_run(self) -> None:
        """Cleans up resources after the pipeline run is finished."""

    def prepare_step_run(self) -> None:
        """Prepares running a step."""

    def cleanup_step_run(self) -> None:
        """Cleans up resources after the step run is finished."""

    @property
    def post_registration_message(self) -> Optional[str]:
        """Optional message that will be printed after the stack component is registered.

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
            f"{key}={value}" for key, value in self.dict().items()
        )
        return (
            f"{self.__class__.__qualname__}(type={self.TYPE}, "
            f"flavor={self.FLAVOR}, {attribute_representation})"
        )

    def __str__(self) -> str:
        """String representation of the stack component.

        Returns:
            A string representation of the stack component.
        """
        return self.__repr__()

    @root_validator(skip_on_failure=True)
    def _ensure_stack_component_complete(cls, values: Dict[str, Any]) -> Any:
        """Ensures that the stack component is complete.

        Args:
            values: The values of the stack component.

        Returns:
            The values of the stack component.

        Raises:
            StackComponentInterfaceError: If the stack component is not
                implemented correctly.
        """
        try:
            stack_component_type = getattr(cls, "TYPE")
            assert stack_component_type in StackComponentType
        except (AttributeError, AssertionError):
            raise StackComponentInterfaceError(
                textwrap.dedent(
                    """
                    When you are working with any classes which subclass from
                    `zenml.stack.StackComponent` please make sure that your
                    class has a ClassVar named `TYPE` and its value is set to a
                    `StackComponentType` from `from zenml.enums import
                    StackComponentType`.

                    In most of the cases, this is already done for you within
                    the implementation of the base concept.

                    Example:

                    class BaseArtifactStore(StackComponent):
                        # Instance Variables
                        path: str

                        # Class Variables
                        TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
                    """
                )
            )

        try:
            getattr(cls, "FLAVOR")
        except AttributeError:
            raise StackComponentInterfaceError(
                textwrap.dedent(
                    """
                    When you are working with any classes which subclass from
                    `zenml.stack.StackComponent` please make sure that your
                    class has a defined ClassVar `FLAVOR`.

                    Example:

                    class LocalArtifactStore(BaseArtifactStore):

                        ...

                        # Define flavor as a ClassVar
                        FLAVOR: ClassVar[str] = "local"

                        ...
                    """
                )
            )

        return values

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
        # prevent extra attributes during model initialization
        extra = Extra.forbid
