#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""ZenML specific exception definitions"""
import textwrap
from typing import TYPE_CHECKING, List, Optional, Type

if TYPE_CHECKING:
    from zenml.steps import BaseStepConfig


class ZenMLBaseException(Exception):
    """Base exception for all ZenML Exceptions."""

    def __init__(
        self,
        message: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """BaseException used to format messages displayed to the user.

        Args:
            message: Message with details of exception. This message
                     will be appended with another message directing user to
                     `url` for more information. If `None`, then default
                     Exception behavior is used.
            url: URL to point to in exception message. If `None`, then no url
                 is appended.
        """
        if message:
            if url:
                message += f" For more information, visit {url}."
        super().__init__(message)


class InitializationException(ZenMLBaseException):
    """Raised when an error occurred during initialization of a ZenML
    repository."""


class ForbiddenRepositoryAccessError(ZenMLBaseException, RuntimeError):
    """Raised when trying to access a ZenML repository instance while a step
    is executed."""


class DoesNotExistException(ZenMLBaseException):
    """Raises exception when the entity does not exist in the system but an
    action is being done that requires it to be present."""

    def __init__(self, message: str):
        super().__init__(message)


class AlreadyExistsException(ZenMLBaseException):
    """Raises exception when the `name` already exist in the system but an
    action is trying to create a resource with the same name."""

    def __init__(
        self,
        message: Optional[str] = None,
        name: str = "",
        resource_type: str = "",
    ):
        if message is None:
            message = f"{resource_type} `{name}` already exists!"
        super().__init__(message)


class PipelineNotSucceededException(ZenMLBaseException):
    """Raises exception when trying to fetch artifacts from a not succeeded
    pipeline."""

    def __init__(
        self,
        name: str = "",
        message: str = "{} is not yet completed successfully.",
    ):
        super().__init__(message.format(name))


class GitException(ZenMLBaseException):
    """Raises exception when a problem occurs in git resolution."""

    def __init__(
        self,
        message: str = "There is a problem with git resolution. "
        "Please make sure that all relevant files "
        "are committed.",
    ):
        super().__init__(message)


class StepInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Step interface
    in an unsupported way."""


class MaterializerInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Materializer interface
    in an unsupported way."""


class StepContextError(ZenMLBaseException):
    """Raises exception when interacting with a StepContext
    in an unsupported way."""


class PipelineInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Pipeline interface
    in an unsupported way."""


class ArtifactInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Artifact interface
    in an unsupported way."""


class StackComponentInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the stack components
    in an unsupported way."""


class ArtifactStoreInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Artifact Store interface
    in an unsupported way."""


class PipelineConfigurationError(ZenMLBaseException):
    """Raises exceptions when a pipeline configuration contains
    invalid values."""


class MissingStepParameterError(ZenMLBaseException):
    """Raises exceptions when a step parameter is missing when running a
    pipeline."""

    def __init__(
        self,
        step_name: str,
        missing_parameters: List[str],
        config_class: Type["BaseStepConfig"],
    ):
        """
        Initializes a MissingStepParameterError object.

        Args:
            step_name: Name of the step for which one or more parameters
                       are missing.
            missing_parameters: Names of all parameters which are missing.
            config_class: Class of the configuration object for which
                          the parameters are missing.
        """
        message = textwrap.fill(
            textwrap.dedent(
                f"""
            Missing parameters {missing_parameters} for '{step_name}' step.
            There are three ways to solve this issue:
            (1) Specify a default value in the configuration class
            `{config_class.__name__}`
            (2) Specify the parameters in code when creating the pipeline:
            `my_pipeline({step_name}(config={config_class.__name__}(...))`
            (3) Specify the parameters in a yaml configuration file and pass
            it to the pipeline: `my_pipeline(...).with_config('path_to_yaml')`
            """
            )
        )
        super().__init__(message)


class IntegrationError(ZenMLBaseException):
    """Raises exceptions when a requested integration can not be activated."""


class DuplicateRunNameError(RuntimeError):
    """Raises exception when a run with the same name already exists."""

    def __init__(
        self,
        message: str = "Unable to run a pipeline with a run name that "
        "already exists.",
    ):
        super().__init__(message)


class StackExistsError(ZenMLBaseException):
    """Raised when trying to register a stack with a name that already
    exists."""


class StackComponentExistsError(ZenMLBaseException):
    """Raised when trying to register a stack component with a name that
    already exists."""


class EntityExistsError(ZenMLBaseException):
    """Raised when trying to register a user-management entity with a name that
    already exists."""


class SecretExistsError(ZenMLBaseException):
    """Raised when trying to register a secret with a name that
    already exists."""


class StackValidationError(ZenMLBaseException):
    """Raised when a stack configuration is not valid."""


class ProvisioningError(ZenMLBaseException):
    """Raised when an error occurs when provisioning resources for a
    StackComponent."""


class GitNotFoundError(ImportError):
    """Raised when ZenML CLI is used to interact with examples on a machine
    with no git installation"""


class DuplicatedConfigurationError(ZenMLBaseException):
    """Raised when a configuration parameter is set twice"""
