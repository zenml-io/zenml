#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""ZenML Dev CLI for managing workspaces and running dev pipelines."""

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import click
import requests

try:
    import docker
    from docker.errors import APIError, BuildError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    BuildError = Exception
    APIError = Exception

from zenml.login.pro.client import AuthorizationException, ZenMLProClient

# Constants for environment variables
ZENML_API_URL_ENV = "ZENML_STORE_URL"
ZENML_API_KEY_ENV = "ZENML_STORE_API_KEY"
ZENML_CONFIG_FILE = os.path.expanduser("~/.zenml/dev_config.json")


BASE_STAGING_URL = "https://staging.cloudapi.zenml.io"

def _disect_docker_image_parts(docker_image: str) -> Tuple[str, str]:
    """Get the image repository and tag from a Docker image.
    
    Args:
        docker_image: The Docker image to disect.
        
    Returns:
        A tuple of (image_repository, image_tag).
    """
    docker_image_parts = docker_image.split(":")
    if len(docker_image_parts) == 1:
        image_repository = docker_image_parts[0]
        image_tag = "latest"
    else:
        image_repository = docker_image_parts[0]
        image_tag = docker_image_parts[1]
    return image_repository, image_tag


def _get_headers(token: str) -> Dict[str, str]:
    """Get the headers for the staging API.
    
    Args:
        token: The access token for the staging API.
        
    Returns:
        A dictionary of headers for the staging API.
    """
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}


def _build_configuration(
    zenml_version: Optional[str],
    docker_image: Optional[str] = None,
    helm_chart_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the configuration for the workspace.
    
    Args:
        zenml_version: The ZenML version to use for the workspace.
        docker_image: The Docker image to use for the workspace.
        helm_chart_version: The Helm chart version to use for the workspace.
        
    Returns:
        The configuration dictionary for the workspace.
    """
    configuration: Dict[str, Any] = {}

    if zenml_version:
        configuration["version"] = zenml_version

    if any([docker_image, helm_chart_version]):
        configuration["admin"] = {}

    if docker_image is not None:
        image_repository, image_tag = _disect_docker_image_parts(docker_image)
        configuration["admin"] = configuration.get("admin", {})
        configuration["admin"]["image_repository"] = image_repository
        configuration["admin"]["image_tag"] = image_tag

    if helm_chart_version is not None:
        configuration["admin"] = configuration.get("admin", {})
        configuration["admin"]["helm_chart_version"] = helm_chart_version

    return configuration


def get_current_git_branch() -> Optional[str]:
    """Get the current git branch name.
    
    Returns:
        The current git branch name, or None if it cannot be determined.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        
        # Handle detached HEAD state
        if branch == "HEAD":
            return None
            
        return branch
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def slugify_branch_name(branch_name: str) -> str:
    """Convert a branch name to a Docker-compatible tag.
    
    Implements the same slugification logic as the GitHub workflow:
    1. Convert to lowercase
    2. Replace invalid chars with dashes
    3. Remove leading non-alphanumeric chars
    4. Replace multiple consecutive dashes with a single dash
    5. Remove trailing dashes
    6. Limit to 128 chars max
    
    Args:
        branch_name: The branch name to slugify.
        
    Returns:
        A Docker-compatible tag derived from the branch name.
    """
    # Convert to lowercase
    slug = branch_name.lower()
    
    # Replace invalid chars with dashes (only allow a-z, 0-9, ., _, -)
    slug = re.sub(r"[^a-z0-9_\.\-]", "-", slug)
    
    # Remove leading non-alphanumeric chars
    slug = re.sub(r"^[^a-z0-9]*", "", slug)
    
    # Replace multiple consecutive dashes with a single dash
    slug = re.sub(r"-+", "-", slug)
    
    # Remove trailing dashes
    slug = re.sub(r"-$", "", slug)
    
    # Limit to 128 chars max
    slug = slug[:128]
    
    # If we end up with an empty string, use "dev" as fallback
    if not slug:
        slug = "dev"
    
    return slug


def get_zenml_version() -> Optional[str]:
    """Get the ZenML version from the VERSION file.
    
    Returns:
        The ZenML version as a string, or None if the VERSION file cannot be found or read.
    """
    # Try different possible locations for the VERSION file
    version_paths = [
        "src/zenml/VERSION",  # When in the zenml repo root
        "../src/zenml/VERSION",  # When in the dev directory
        "../../src/zenml/VERSION",  # When in a subdirectory of dev
    ]
    
    for path in version_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    # Read and remove any whitespace
                    return f.read().strip()
            except (IOError, OSError):
                pass
    
    return None


def get_default_workspace_name() -> str:
    """Get a default workspace name based on the current git branch.
    
    Returns:
        A slugified version of the current git branch name, or "dev" if the branch
        cannot be determined.
    """
    branch = get_current_git_branch()
    if branch:
        return slugify_branch_name(branch)
    else:
        return "dev"


def get_token(client_id: str, client_secret: str) -> str:
    """Get an access token for the staging API.
    
    Args:
        client_id: The client ID for authentication with the API.
        client_secret: The client secret for authentication with the API.
        
    Returns:
        A valid access token as a string.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/auth/login"
    data = {
        "grant_type": "",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    response = requests.post(url, data=data)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )

    return response.json()["access_token"]


def get_workspace(token: str, workspace_name_or_id: str) -> Dict[str, Any]:
    """Get a workspace by name or ID.
    
    Args:
        token: The access token for authentication with the API.
        workspace_name_or_id: The name or ID of the workspace to retrieve.
        
    Returns:
        The workspace information as a dictionary.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/workspaces/{workspace_name_or_id}"

    response = requests.get(url, headers=_get_headers(token))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )

    return response.json()


def create_workspace(
    token: str,
    workspace_name: str,
    organization_id: str,
    configuration: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new ZenML workspace.
    
    Args:
        token: The access token for authentication with the API.
        workspace_name: The name for the new workspace.
        organization_id: The ID of the organization to create the workspace in.
        configuration: The configuration settings for the workspace.
        
    Returns:
        The created workspace information as a dictionary.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/workspaces"

    data = {
        "name": workspace_name,
        "organization_id": organization_id,
        "zenml_service": {
            "configuration": configuration,
        },
    }
    response = requests.post(url, headers=_get_headers(token), json=data)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )

    return response.json()


def update_workspace(
    token: str,
    workspace_name_or_id: str,
    configuration: Dict[str, Any],
) -> None:
    """Update an existing ZenML workspace.
    
    Args:
        token: The access token for authentication with the API.
        workspace_name_or_id: The name or ID of the workspace to update.
        configuration: The new configuration settings for the workspace.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/workspaces/{workspace_name_or_id}"

    data = {
        "zenml_service": {"configuration": configuration},
        "desired_state": "available",
    }

    response = requests.patch(
        url, json=data, headers=_get_headers(token), params={"force": True}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )


def destroy_workspace(token: str, workspace_id: UUID) -> None:
    """Destroy (delete) a ZenML workspace.
    
    Args:
        token: The access token for authentication with the API.
        workspace_id: The UUID of the workspace to destroy.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/workspaces/{workspace_id}"

    response = requests.delete(url, headers=_get_headers(token))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )


def wait_for_availability(token: str, workspace_name_or_id: str, timeout: int = 600) -> None:
    """Wait for a workspace to become available.
    
    Polls the workspace status until it transitions from 'pending' to 'available'
    or until the timeout is reached.
    
    Args:
        token: The access token for authentication with the API.
        workspace_name_or_id: The name or ID of the workspace to wait for.
        timeout: Maximum time to wait in seconds (default: 600).
        
    Raises:
        RuntimeError: If the workspace fails to become available or if the timeout is reached.
    """
    sleep_period = 10
    deadline = time.time() + timeout
    workspace = get_workspace(token, workspace_name_or_id)

    click.echo("Waiting for workspace to become available...")
    
    while workspace["status"] == "pending":
        click.echo(f"Current status: {workspace['status']}. Waiting...")

        if time.time() > deadline:
            raise RuntimeError(
                "Timed out! The workspace could be stuck in a `pending` state."
            )

        time.sleep(sleep_period)
        workspace = get_workspace(token, workspace_name_or_id)

    if workspace["status"] != "available":
        raise RuntimeError(f"Workspace creation failed with status: {workspace['status']}")
    
    click.echo(f"Workspace is available! Status: {workspace['status']}")


def get_auth_token() -> str:
    """Get authentication token from environment variables or ZenML Pro Client.
    
    Checks for authentication credentials in environment variables and
    if not found, tries to use the ZenML Pro Client's existing authentication.
    
    Returns:
        A valid authentication token.
        
    Raises:
        ValueError: If required authentication credentials are not found.
    """
    client_id = os.environ.get("CLOUD_STAGING_CLIENT_ID")
    client_secret = os.environ.get("CLOUD_STAGING_CLIENT_SECRET")

    if client_id and client_secret:
        return get_token(client_id, client_secret)
    
    # Try to use ZenML Pro Client if credentials not in environment variables
    try:
        
        click.echo("Credentials not found in environment variables. Trying to use existing ZenML authentication...")
        client = ZenMLProClient(url=BASE_STAGING_URL)
        api_token = client.api_token
        
        if api_token:
            click.echo("Using existing ZenML authentication")
            return api_token
        else:
            raise ValueError("Could not get authentication token from ZenML Pro Client")
    
    except AuthorizationException:
        raise ValueError(
            "You are not logged in to ZenML. Please either login with 'zenml login' "
            "or set CLOUD_STAGING_CLIENT_ID and CLOUD_STAGING_CLIENT_SECRET environment variables."
        )
    except Exception as e:
        raise ValueError(
            f"Failed to authenticate: {str(e)}. Please either login with 'zenml login' "
            "or set CLOUD_STAGING_CLIENT_ID and CLOUD_STAGING_CLIENT_SECRET environment variables."
        )


@click.group()
def cli():
    """ZenML Dev CLI for managing workspaces and running pipelines."""
    pass


@cli.command("deploy")
@click.option(
    "--workspace", 
    help="Name of the workspace to create (defaults to slugified git branch name)",
    default=None
)
@click.option(
    "--organization", 
    help="Organization ID",
    envvar="DEV_ORGANIZATION_ID"
)
@click.option(
    "--zenml-version",
    help="ZenML version to use (defaults to value from VERSION file)",
    default=None
)
@click.option(
    "--helm-version", 
    help="Helm chart version to use"
)
@click.option(
    "--docker-image", 
    help="Docker image to use (format: repository:tag)"
)
def deploy(
    workspace: Optional[str],
    organization: str,
    zenml_version: Optional[str],
    helm_version: Optional[str],
    docker_image: Optional[str],
):
    """Deploy a new workspace with the given configuration.
    
    Creates a new ZenML workspace in the cloud environment with the specified
    configuration parameters. This command will wait for the workspace to become
    available before returning.
    
    If no workspace name is provided, uses the current git branch name (slugified).
    If no ZenML version is provided, uses the version from the VERSION file.
    
    Args:
        workspace: Name of the workspace to create.
        organization: Organization ID. Defaults to ZENML_DEV_ORGANIZATION_ID env var.
        zenml_version: ZenML version to use for the workspace.
        helm_version: Helm chart version to use for the workspace deployment.
        docker_image: Docker image to use, in the format repository:tag.
        
    Examples:
        $ ./zen-dev deploy
        $ ./zen-dev deploy --workspace my-workspace --zenml-version 0.40.0
        $ ./zen-dev deploy --zenml-version 0.40.0 --docker-image zenmldocker/zenml-server:custom
    """
    # Use default workspace name if not provided
    if workspace is None:
        workspace = get_default_workspace_name()
        click.echo(f"Using git branch as workspace name: {workspace}")
    
    # Use default ZenML version if not provided
    if zenml_version is None:
        zenml_version = get_zenml_version()
        if zenml_version:
            click.echo(f"Using ZenML version from VERSION file: {zenml_version}")
        else:
            click.echo("Warning: No ZenML version specified and VERSION file not found")
            return
    
    click.echo(f"Deploying workspace: {workspace}")
    
    token = get_auth_token()

    configuration = _build_configuration(
        zenml_version=zenml_version,
        docker_image=docker_image,
        helm_chart_version=helm_version,
    )
    
    try:
        workspace_data = create_workspace(
            token=token,
            workspace_name=workspace,
            organization_id=organization,
            configuration=configuration,
        )
        click.echo(f"Workspace created with ID: {workspace_data['id']}")
        
        wait_for_availability(token, workspace_data["id"])
            
        click.echo(
            "Workspace deployed! Access it at: "
            f"https://staging.cloud.zenml.io/workspaces/{workspace}/projects"
        )
    except Exception as e:
        click.echo(f"Error deploying workspace: {str(e)}", err=True)
        sys.exit(1)


@cli.command("update")
@click.option(
    "--workspace", 
    help="Name or ID of the workspace to update (defaults to slugified git branch name)",
    default=None
)
@click.option(
    "--zenml-version", 
    help="ZenML version to use (defaults to value from VERSION file)",
    default=None
)
@click.option(
    "--helm-version", 
    help="Helm chart version to use"
)
@click.option(
    "--docker-image", 
    help="Docker image to use (format: repository:tag)"
)
def update(
    workspace: Optional[str],
    zenml_version: Optional[str],
    helm_version: Optional[str],
    docker_image: Optional[str],
):
    """Update an existing workspace with the given configuration.
    
    Updates the configuration of an existing ZenML workspace in the cloud 
    environment. This command will wait for the workspace update to complete
    before returning.
    
    If no workspace name is provided, uses the current git branch name (slugified).
    If no ZenML version is provided, uses the version from the VERSION file.
    
    Args:
        workspace: Name or ID of the workspace to update.
        zenml_version: New ZenML version to use for the workspace.
        helm_version: New Helm chart version to use for the workspace.
        docker_image: New Docker image to use, in the format repository:tag.
        
    Examples:
        $ ./zen-dev update
        $ ./zen-dev update --workspace my-workspace --zenml-version 0.40.1
        $ ./zen-dev update --docker-image zenmldocker/zenml-server:new-tag
    """
    # Use default workspace name if not provided
    if workspace is None:
        workspace = get_default_workspace_name()
        click.echo(f"Using git branch as workspace name: {workspace}")
    
    # Use default ZenML version if not provided
    if zenml_version is None:
        zenml_version = get_zenml_version()
        if zenml_version:
            click.echo(f"Using ZenML version from VERSION file: {zenml_version}")
        else:
            click.echo("Warning: No ZenML version specified and VERSION file not found")
            return
    
    click.echo(f"Updating workspace: {workspace}")

    token = get_auth_token()
    configuration = _build_configuration(
        zenml_version=zenml_version,
        docker_image=docker_image,
        helm_chart_version=helm_version,
    )

    workspace_response = get_workspace(token, workspace)

    try:
        update_workspace(
            token=token,
            workspace_name_or_id=workspace_response["id"],
            configuration=configuration,
        )
        click.echo("Workspace update initiated")
        
        wait_for_availability(token, workspace)
            
        click.echo(
            "Workspace updated! Access it at: "
            f"https://staging.cloud.zenml.io/workspaces/{workspace}/projects"
        )
    except Exception as e:
        click.echo(f"Error updating workspace: {str(e)}", err=True)
        sys.exit(1)


@cli.command("destroy")
@click.option(
    "--workspace", 
    required=False,
    help="ID or name of the workspace to destroy (defaults to slugified git branch name)"
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt"
)
def destroy(workspace: Optional[str], force: bool):
    """Destroy an existing workspace.
    
    Permanently deletes a ZenML workspace and all associated resources.
    By default, this command will prompt for confirmation before proceeding.
    
    If no workspace is provided, uses the current git branch name (slugified).
    
    Args:
        workspace: ID or name of the workspace to destroy.
        force: If True, skip the confirmation prompt.
        
    Examples:
        $ ./zen-dev destroy
        $ ./zen-dev destroy --workspace my-workspace
        $ ./zen-dev destroy --workspace 123e4567-e89b-12d3-a456-426614174000 --force
    """
    # Use default workspace name if not provided
    if workspace is None:
        workspace = get_default_workspace_name()
        click.echo(f"Using git branch as workspace name: {workspace}")
    
    if not force:
        confirm = click.confirm(
            f"Are you sure you want to destroy workspace '{workspace}'? "
            "This action cannot be undone."
        )
        if not confirm:
            click.echo("Operation cancelled.")
            return
    
    click.echo(f"Destroying workspace: {workspace}")
    
    token = get_auth_token()
    
    try:
        # If the workspace is provided as a name (not UUID), get the ID first
        try:
            uuid_obj = UUID(workspace)
            workspace_id = workspace
        except ValueError:
            # If not a valid UUID, assume it's a name and get the workspace info
            workspace_info = get_workspace(token, workspace)
            workspace_id = workspace_info["id"]
            click.echo(f"Found workspace ID: {workspace_id}")

        destroy_workspace(token, UUID(workspace_id))
        click.echo(f"✅ Workspace '{workspace}' destroyed successfully.")
    except Exception as e:
        click.echo(f"❌ Error destroying workspace: {str(e)}", err=True)
        sys.exit(1)


def get_workspace_auth_token(token: str, workspace_id: str) -> str:
    """Get a workspace-specific authorization token.
    
    Args:
        token: The access token for the cloud API.
        workspace_id: The ID of the workspace to get an authorization token for.
        
    Returns:
        A workspace-specific authorization token.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{BASE_STAGING_URL}/auth/workspace_authorization/{workspace_id}"
    response = requests.get(url, headers=_get_headers(token))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )
    
    return response.json()["access_token"]


def authenticate_with_workspace(server_url: str, workspace_auth_token: str) -> Tuple[str, str]:
    """Authenticate with a workspace and get auth cookie and CSRF token.
    
    Args:
        server_url: The URL of the workspace server.
        workspace_auth_token: The workspace-specific authorization token.
        
    Returns:
        A tuple of (auth_cookie, csrf_token) for subsequent API requests.
        
    Raises:
        RuntimeError: If authentication fails or if the required tokens are not found.
    """
    url = f"{server_url}/api/v1/login"
    headers = {
        "Authorization": f"Bearer {workspace_auth_token}",
        "accept": "application/json"
    }

    response = requests.post(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )
    
    cookies = response.cookies.get_dict()
    csrf_token = response.json().get("csrf_token")
    
    auth_cookie = cookies.get("zenml-auth")
    if auth_cookie is None or csrf_token is None:
        raise RuntimeError("Failed to get auth cookie or CSRF token from response")
    
    return auth_cookie, csrf_token


def get_service_account(
    server_url: str,
    auth_cookie: str,
    csrf_token: str,
    service_account_name: str
) -> Optional[Dict[str, Any]]:
    """Get a service account by name.
    
    Uses the direct endpoint to get a service account by name or ID,
    which is more efficient than listing all service accounts.
    
    Args:
        server_url: The URL of the workspace server.
        auth_cookie: The authentication cookie for the workspace.
        csrf_token: The CSRF token for the workspace.
        service_account_name: The name of the service account to get.
        
    Returns:
        The service account information as a dictionary, or None if not found.
        
    Raises:
        RuntimeError: If the API request fails for any reason other than 404.
    """
    url = f"{server_url}/api/v1/service_accounts/{service_account_name}"
    headers = {
        "Cookie": f"zenml-auth={auth_cookie}",
        "X-CSRF-Token": csrf_token,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise RuntimeError(
            f"Request failed with response content: {e.response.text}"
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Request failed: {str(e)}")


def create_service_account(
    server_url: str, 
    auth_cookie: str, 
    csrf_token: str, 
    name: str, 
    description: str
) -> Dict[str, Any]:
    """Create a service account in a workspace.
    
    Args:
        server_url: The URL of the workspace server.
        auth_cookie: The authentication cookie for the workspace.
        csrf_token: The CSRF token for the workspace.
        name: The name for the new service account.
        description: The description for the new service account.
        
    Returns:
        The created service account information as a dictionary.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{server_url}/api/v1/service_accounts"
    headers = {
        "Cookie": f"zenml-auth={auth_cookie}",
        "X-CSRF-Token": csrf_token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "description": description,
        "active": True
    }
    
    response = requests.post(url, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )
    
    return response.json()


def create_api_key(
    server_url: str,
    auth_cookie: str,
    csrf_token: str,
    service_account_id: str,
    name: str,
    description: str
) -> Dict[str, Any]:
    """Create an API key for a service account.
    
    Args:
        server_url: The URL of the workspace server.
        auth_cookie: The authentication cookie for the workspace.
        csrf_token: The CSRF token for the workspace.
        service_account_id: The ID of the service account to create the key for.
        name: The name for the new API key.
        description: The description for the new API key.
        
    Returns:
        The created API key information as a dictionary.
        
    Raises:
        RuntimeError: If the API request fails for any reason.
    """
    url = f"{server_url}/api/v1/service_accounts/{service_account_id}/api_keys"
    headers = {
        "Cookie": f"zenml-auth={auth_cookie}",
        "X-CSRF-Token": csrf_token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "description": description
    }
    
    response = requests.post(url, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )
    
    return response.json()


@cli.command("gh-action-login")
def gh_action_login():
    """(FOR GH ACTIONS ONLY) Authenticate with a workspace with a service account.
    
    This command authenticates with the GH Runner with a ZenML workspace using
    the current git branch name as the workspace name. It creates or reuses a
    service account with a standardized name, and generates an API key. It
    outputs GitHub Actions compatible commands that mask secrets and set outputs
    for subsequent steps.
    
    Examples:
        $ ./zen-dev gh-action-login
    """
    try:
        # Use git branch name for workspace
        workspace = get_default_workspace_name()
        click.echo(f"Using git branch as workspace name: {workspace}")
            
        token = get_auth_token()
        
        # Get workspace information
        workspace_info = get_workspace(token, workspace)
        workspace_id = workspace_info["id"]
        workspace_name = workspace_info["name"]
        server_url = workspace_info["zenml_service"]["status"]["server_url"]
        
        click.echo(f"Workspace found: {workspace_name} (ID: {workspace_id})")
        
        # Get workspace authorization token
        workspace_auth_token = get_workspace_auth_token(token, workspace_id)
        
        # Authenticate with the workspace
        auth_cookie, csrf_token = authenticate_with_workspace(server_url, workspace_auth_token)
        
        # Create standard service account name based on workspace name
        sa_name = f"github-actions-{workspace_name}"
        sa_description = "Service account for GitHub Actions"
        
        # Check if service account already exists using direct endpoint
        existing_sa = get_service_account(
            server_url, auth_cookie, csrf_token, sa_name
        )
        
        if existing_sa:
            click.echo(f"Using existing service account: {sa_name} (ID: {existing_sa['id']})")
            service_account_id = existing_sa["id"]
        else:
            # Create a new service account
            service_account = create_service_account(
                server_url, auth_cookie, csrf_token, sa_name, sa_description
            )
            service_account_id = service_account["id"]
            click.echo(f"Service account created: {sa_name} (ID: {service_account_id})")
        
        # Create an API key
        api_key_name = f"{sa_name}-key"
        api_key_description = "API key for GitHub Actions"
        api_key_info = create_api_key(
            server_url, auth_cookie, csrf_token, service_account_id, 
            api_key_name, api_key_description
        )
        
        api_key = api_key_info["body"]["key"]
        click.echo(f"API key created: {api_key_name}")
        
        # Output GitHub Actions format
        print(f"::add-mask::{api_key}")
        print(f"::set-output name=server_url::{server_url}")
        print(f"::set-output name=api_key::{api_key}")
                
    except Exception as e:
        click.echo(f"Error authenticating with workspace: {str(e)}", err=True)
        sys.exit(1)


@cli.command("info")
def info():
    """Display information about the current development environment.
    
    Shows the detected ZenML version from the VERSION file and the
    slugified branch name that would be used as a workspace name.
    
    Examples:
        $ ./zen-dev info
    """
    branch = get_current_git_branch()
    if branch:
        click.echo(f"Current git branch: {branch}")
        slug = slugify_branch_name(branch)
        click.echo(f"Slugified name: {slug}")
    else:
        click.echo("No git branch detected")
        click.echo("Default workspace name: dev")
    
    version = get_zenml_version()
    if version:
        click.echo(f"ZenML version: {version}")
    else:
        click.echo("ZenML version: Could not determine (VERSION file not found)")


@cli.command("build")
@click.option(
    "--server", 
    is_flag=True,
    help="Build the zenml-server image instead of zenml"
)
@click.option(
    "--repo",
    required=True,
    help="Docker repository name (required)",
    envvar="DEV_DOCKER_REPO"
)
@click.option(
    "--tag",
    default=None,
    help="Tag for the Docker image (defaults to slugified git branch name)"
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the image after building"
)
def build(server: bool, repo: str, tag: Optional[str], push: bool):
    """Build a ZenML Docker image.
    
    This command builds a Docker image for ZenML or ZenML Server using
    the appropriate dev Dockerfile. By default, it builds the zenml image, 
    but you can use --server to build the zenml-server image instead.
    
    If no tag is provided, uses the current git branch name (slugified).
    
    Args:
        server: If True, build the zenml-server image instead of zenml.
        repo: Docker repository name (required, can be set with DEV_DOCKER_REPO env var).
        tag: Tag for the Docker image (defaults to slugified git branch name).
        push: If True, push the image after building.
        
    Examples:
        $ ./zen-dev build --repo zenmldocker
        $ ./zen-dev build --server --repo zenmldocker
        $ ./zen-dev build --repo zenmldocker --tag v1.0
        $ ./zen-dev build --repo myrepo --tag test
        $ ./zen-dev build --repo zenmldocker --push
    """
    if not DOCKER_AVAILABLE:
        click.echo("Docker Python client not found. Please install with 'pip install docker'", err=True)
        sys.exit(1)
    
    # Use slugified git branch name as default tag if not provided
    if tag is None:
        tag = get_default_workspace_name()
        click.echo(f"Using git branch as tag: {tag}")
    
    # Determine image type
    image_type = "zenml-server" if server else "zenml"
    image_name = f"{repo}/{image_type}:{tag}"
    
    # Build the Docker image
    click.echo(f"Building Docker image: {image_name}...")
    
    try:
        client = docker.from_env()
        
        # Find the Dockerfile path
        dockerfile_path = f"docker/{image_type}-dev.Dockerfile"
        if not os.path.exists(dockerfile_path):
            click.echo(f"Error: Dockerfile not found at {dockerfile_path}", err=True)
            sys.exit(1)
        
        # Build the image
        click.echo("Building image... (this may take a while)")
        image, logs = client.images.build(
            path=".",
            dockerfile=dockerfile_path,
            tag=image_name,
            buildargs={"PYTHON_VERSION": "3.11"},
            platform="linux/amd64",
            rm=True
        )
        
        # Check for errors
        for log in logs:
            if isinstance(log, dict) and "error" in log:
                error = log.get("error", "")
                if isinstance(error, str):
                    click.echo(f"Error building image: {error}", err=True)
                    sys.exit(1)
        
        click.echo(f"✅ Successfully built: {image_name}")
        
        # Push the image if requested
        if push:
            click.echo(f"Pushing Docker image: {image_name}...")
            click.echo("Pushing image... (this may take a while)")
            
            repository = f"{repo}/{image_type}"
            
            # Push the image and check for errors
            for line in client.images.push(repository=repository, tag=tag, stream=True, decode=True):
                if isinstance(line, dict) and "error" in line:
                    error = line.get("error", "")
                    if isinstance(error, str):
                        click.echo(f"Error pushing image: {error}", err=True)
                        sys.exit(1)
            
            click.echo(f"✅ Successfully pushed: {image_name}")
    
    except BuildError as e:
        click.echo(f"❌ Error building image: {str(e)}", err=True)
        sys.exit(1)
    except APIError as e:
        click.echo(f"❌ Docker API error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli() 