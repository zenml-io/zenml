#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Authentication utilities for ZenML."""

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import LOCAL_STORES_DIRECTORY_NAME
from zenml.exceptions import AuthorizationException, CredentialsNotValid
from zenml.logger import get_logger

logger = get_logger(__name__)


def require_user_authentication(
    bypass_local_check: bool = False,
    context: str = "run pipelines",
) -> None:
    """Check if user is authenticated and raise error if not.

    This function enforces mandatory authentication for pipeline execution and
    other critical operations. It checks if the user has valid authentication
    credentials and raises an error if not.

    Args:
        bypass_local_check: If True, skips the check for local stores
            (used for operations that always require server connectivity).
        context: Description of the operation requiring authentication
            (e.g., "run pipelines", "access model registry").

    Raises:
        CredentialsNotValid: If user is not authenticated with helpful error message.
    """
    import os

    # Allow bypassing authentication check via environment variable (for testing)
    if os.environ.get("ZENML_DISABLE_LOGIN_REQUIREMENT", "").lower() in [
        "true",
        "1",
        "yes",
    ]:
        logger.debug(
            "Bypassing authentication check due to ZENML_DISABLE_LOGIN_REQUIREMENT"
        )
        return

    client = Client()
    global_config = GlobalConfiguration()

    # Check if we're using a local store (SQLite) and bypass_local_check is False
    if not bypass_local_check:
        store_config = global_config.store_configuration
        if store_config and store_config.url:
            # Check for local SQLite stores
            if (
                store_config.url.startswith("sqlite:")
                or LOCAL_STORES_DIRECTORY_NAME in str(store_config.url)
                or global_config.local_stores_path in str(store_config.url)
            ):
                # For local stores, we don't require authentication
                logger.debug(
                    f"Skipping authentication check for local store: {store_config.url}"
                )
                return

    try:
        # Try to get the active user - this will trigger authentication
        user = client.active_user
        if user:
            # Successfully authenticated
            logger.debug(f"User {user.name} is authenticated")
            return
    except CredentialsNotValid as e:
        # Extract server URL from the store configuration for better error message
        store_config = global_config.store_configuration
        server_url = ""
        if store_config and store_config.url:
            server_url = store_config.url

        # Create helpful error message based on the specific authentication error
        error_msg = str(e)
        if "No valid credentials found" in error_msg:
            if server_url:
                error_message = (
                    f"You must be logged in to {context}. "
                    f"Please run 'zenml login --url {server_url}' to authenticate."
                )
            else:
                error_message = (
                    f"You must be logged in to {context}. "
                    "Please run 'zenml login' to authenticate with a ZenML server."
                )
        elif (
            "authentication to the current server has expired"
            in error_msg.lower()
        ):
            if server_url:
                error_message = (
                    f"Your authentication has expired. "
                    f"Please run 'zenml login --url {server_url}' to re-authenticate."
                )
            else:
                error_message = (
                    "Your authentication has expired. "
                    "Please run 'zenml login' to re-authenticate."
                )
        else:
            # Generic authentication error
            if server_url:
                error_message = (
                    f"Authentication failed: {error_msg} "
                    f"Please run 'zenml login --url {server_url}' to authenticate."
                )
            else:
                error_message = (
                    f"Authentication failed: {error_msg} "
                    "Please run 'zenml login' to authenticate with a ZenML server."
                )

        # Raise CredentialsNotValid with the enhanced error message
        raise CredentialsNotValid(error_message) from e
    except AuthorizationException:
        # Handle servers with NO_AUTH scheme or other authorization issues
        # that don't require explicit user authentication
        try:
            # Check if we can connect to the server at all
            # If we can get server info, the server might be running NO_AUTH
            server_info = client.zen_store.get_store_info()
            if server_info:
                logger.debug(
                    "Server connection successful - may be using NO_AUTH scheme"
                )
                return
        except Exception:
            # If we can't even connect to the store, continue with the
            # credential error handling below
            pass

        # If we reach here, it's an authorization error we can't handle
        error_message = (
            f"Authorization failed. "
            "Please ensure you are logged in with 'zenml login'."
        )
        raise CredentialsNotValid(error_message)
    except Exception as e:
        # Handle any other unexpected authentication issues
        error_message = (
            f"Unable to verify authentication status: {str(e)} "
            "Please ensure you are logged in with 'zenml login'."
        )
        raise CredentialsNotValid(error_message) from e


def require_pipeline_execution_authentication() -> None:
    """Convenience function to check authentication for pipeline execution.

    Raises:
        CredentialsNotValid: If user is not authenticated.
    """
    require_user_authentication(context="run pipelines")


def cli_require_login(bypass_local_check: bool = False) -> None:
    """CLI-specific authentication check that raises ClickException on failure.

    This is a wrapper around require_user_authentication that converts
    CredentialsNotValid exceptions to Click exceptions for CLI usage.

    Args:
        bypass_local_check: If True, skips the check for local stores.

    Raises:
        ClickException: If user is not authenticated.
    """
    import click

    try:
        require_user_authentication(
            bypass_local_check=bypass_local_check, context="run pipelines"
        )
    except CredentialsNotValid as e:
        # Convert to CLI error
        raise click.ClickException(
            message=click.style(str(e), fg="red", bold=True)
        ) from e
