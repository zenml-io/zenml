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
"""ZenML specific exception definitions."""

from typing import TYPE_CHECKING, Dict, List, Optional, Type

if TYPE_CHECKING:
    from zenml.steps import BaseParameters


class ZenMLBaseException(Exception):
    """Base exception for all ZenML Exceptions."""

    def __init__(
        self,
        message: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """The BaseException used to format messages displayed to the user.

        Args:
            message: Message with details of exception. This message
                     will be appended with another message directing user to
                     `url` for more information. If `None`, then default
                     Exception behavior is used.
            url: URL to point to in exception message. If `None`, then no url
                 is appended.
        """
        if message and url:
            message += f" For more information, visit {url}."
        super().__init__(message)


class InitializationException(ZenMLBaseException):
    """Raised when an error occurred during initialization of a ZenML repository."""


class AuthorizationException(ZenMLBaseException):
    """Raised when an authorization error occurred while trying to access a ZenML resource ."""


class DoesNotExistException(ZenMLBaseException):
    """Raises exception when the entity does not exist in the system but an action is being done that requires it to be present."""

    def __init__(self, message: str):
        """Initializes the exception.

        Args:
            message: Message with details of exception.
        """
        super().__init__(message)


class PipelineNotSucceededException(ZenMLBaseException):
    """Raises exception when trying to fetch artifacts from a not succeeded pipeline."""

    def __init__(
        self,
        name: str = "",
        message: str = "{} is not yet completed successfully.",
    ):
        """Initializes the exception.

        Args:
            name: Name of the pipeline.
            message: Message with details of exception.
        """
        super().__init__(message.format(name))


class GitException(ZenMLBaseException):
    """Raises exception when a problem occurs in git resolution."""

    def __init__(
        self,
        message: str = "There is a problem with git resolution. "
        "Please make sure that all relevant files "
        "are committed.",
    ):
        """Initializes the exception.

        Args:
            message: Message with details of exception.
        """
        super().__init__(message)


class StepInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Step interface in an unsupported way."""


class MaterializerInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Materializer interface in an unsupported way."""


class StepContextError(ZenMLBaseException):
    """Raises exception when interacting with a StepContext in an unsupported way."""


class PipelineInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Pipeline interface in an unsupported way."""


class ArtifactInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Artifact interface in an unsupported way."""


class StackComponentInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the stack components in an unsupported way."""


class StackComponentDeploymentError(ZenMLBaseException):
    """Raises exception when deploying a stack component fails."""


class ArtifactStoreInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Artifact Store interface in an unsupported way."""


class PipelineConfigurationError(ZenMLBaseException):
    """Raises exceptions when a pipeline configuration contains invalid values."""


class MissingStepParameterError(ZenMLBaseException):
    """Raises exceptions when a step parameter is missing when running a pipeline."""

    def __init__(
        self,
        step_name: str,
        missing_parameters: List[str],
        parameters_class: Type["BaseParameters"],
    ):
        """Initializes a MissingStepParameterError object.

        Args:
            step_name: Name of the step for which one or more parameters
                are missing.
            missing_parameters: Names of all parameters which are missing.
            parameters_class: Class of the parameters object for which
                the parameters are missing.
        """
        import textwrap

        message = textwrap.fill(
            textwrap.dedent(
                f"""
            Missing parameters {missing_parameters} for '{step_name}' step.
            There are three ways to solve this issue:
            (1) Specify a default value in the parameters class
            `{parameters_class.__name__}`
            (2) Specify the parameters in code when creating the pipeline:
            `my_pipeline({step_name}(params={parameters_class.__name__}(...))`
            (3) Specify the parameters in a yaml configuration file and pass
            it to the pipeline: `my_pipeline(...).run(config_path='path_to_yaml')`
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
        """Initializes the exception.

        Args:
            message: Message with details of exception.
        """
        super().__init__(message)


class ValidationError(ZenMLBaseException):
    """Raised when the Model passed to the ZenStore."""


class EntityExistsError(ZenMLBaseException):
    """Raised when trying to register an entity that already exists."""


class StackExistsError(EntityExistsError):
    """Raised when trying to register a stack with name that already exists."""


class StackComponentExistsError(EntityExistsError):
    """Raised when trying to register a stack component with existing name."""


class SecretExistsError(EntityExistsError):
    """Raised when trying to register a secret with existing name."""


class StackValidationError(ZenMLBaseException):
    """Raised when a stack configuration is not valid."""


class StackComponentValidationError(ZenMLBaseException):
    """Raised when a stack component configuration is not valid."""


class ProvisioningError(ZenMLBaseException):
    """Raised when an error occurs when provisioning resources for a StackComponent."""


class GitNotFoundError(ImportError):
    """Raised when ZenML CLI is used to interact with examples on a machine with no git installation."""


class DuplicatedConfigurationError(ZenMLBaseException):
    """Raised when a configuration parameter is set twice."""


class IllegalOperationError(ZenMLBaseException):
    """Raised when an illegal operation is attempted."""


class SettingsResolvingError(ZenMLBaseException):
    """Raised when resolving settings failed."""


class InputResolutionError(ZenMLBaseException):
    """Raised when step input resolving failed."""


class HydrationError(ZenMLBaseException):
    """Raised when the model hydration failed."""


class ZenKeyError(KeyError):
    """Specialized key error which allows error messages with line breaks."""

    def __init__(self, message: str) -> None:
        """Initialization.

        Args:
            message:str, the error message
        """
        self.message = message

    def __str__(self) -> str:
        """String function.

        Returns:
            the error message
        """
        return self.message


class OAuthError(ValueError):
    """OAuth2 error."""

    def __init__(
        self,
        error: str,
        status_code: int = 400,
        error_description: Optional[str] = None,
        error_uri: Optional[str] = None,
    ) -> None:
        """Initializes the OAuthError.

        Args:
            status_code: HTTP status code.
            error: Error code.
            error_description: Error description.
            error_uri: Error URI.
        """
        self.status_code = status_code
        self.error = error
        self.error_description = error_description
        self.error_uri = error_uri

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Returns the OAuthError as a dictionary.

        Returns:
            The OAuthError as a dictionary.
        """
        return {
            "error": self.error,
            "error_description": self.error_description,
            "error_uri": self.error_uri,
        }

    def __str__(self) -> str:
        """String function.

        Returns:
            the error message
        """
        return f"{self.error}: {self.error_description or ''}"
