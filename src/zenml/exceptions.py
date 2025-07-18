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

from typing import Dict, Optional


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


class CredentialsNotValid(AuthorizationException):
    """Raised when the credentials provided are invalid.

    This is a subclass of AuthorizationException and should only be raised when
    the authentication credentials are invalid (e.g. expired API token, invalid
    username/password, invalid signature). If caught by the ZenML client, it
    will trigger an invalidation of the currently cached API token and a
    re-authentication flow.
    """


class DoesNotExistException(ZenMLBaseException):
    """Raises exception when the entity does not exist in the system but an action is being done that requires it to be present."""

    def __init__(self, message: str):
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


class StackComponentInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the stack components in an unsupported way."""


class ArtifactStoreInterfaceError(ZenMLBaseException):
    """Raises exception when interacting with the Artifact Store interface in an unsupported way."""


class IntegrationError(ZenMLBaseException):
    """Raises exceptions when a requested integration can not be activated."""


class ValidationError(ZenMLBaseException):
    """Raised when the Model passed to the ZenStore."""


class EntityExistsError(ZenMLBaseException):
    """Raised when trying to register an entity that already exists."""


class EntityCreationError(ZenMLBaseException, RuntimeError):
    """Raised when failing to create an entity."""


class WebhookInactiveError(ZenMLBaseException):
    """Raised when source is inactive."""


class StackValidationError(ZenMLBaseException):
    """Raised when a stack configuration is not valid."""


class GitNotFoundError(ImportError):
    """Raised when ZenML CLI is used to interact with examples on a machine with no git installation."""


class IllegalOperationError(ZenMLBaseException):
    """Raised when an illegal operation is attempted."""


class RunStoppedException(ZenMLBaseException):
    """Raised when a ZenML pipeline run gets stopped by the user."""


class RunInterruptedException(ZenMLBaseException):
    """Raised when a ZenML step gets interrupted for an unknown reason."""


class MethodNotAllowedError(ZenMLBaseException):
    """Raised when the server does not allow a request method."""


class SettingsResolvingError(ZenMLBaseException):
    """Raised when resolving settings failed."""


class InputResolutionError(ZenMLBaseException):
    """Raised when step input resolving failed."""


class SubscriptionUpgradeRequiredError(ZenMLBaseException):
    """Raised when user tries to perform an action outside their current subscription tier."""


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


class SecretsStoreNotConfiguredError(NotImplementedError):
    """Raised when a secrets store is not configured."""


class BackupSecretsStoreNotConfiguredError(NotImplementedError):
    """Raised when a backup secrets store is not configured."""


class CustomFlavorImportError(ImportError):
    """Raised when failing to import a custom flavor."""


class MaxConcurrentTasksError(ZenMLBaseException):
    """Raised when the maximum number of concurrent tasks is reached."""


class RunMonitoringError(ZenMLBaseException):
    """Raised when an error occurs while monitoring a pipeline run."""

    def __init__(
        self,
        original_exception: BaseException,
    ) -> None:
        """Initializes the error.

        Args:
            original_exception: The original exception that occurred while
                monitoring the pipeline run.
        """
        self.original_exception = original_exception
