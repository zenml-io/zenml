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
"""A script to manage a ZenML workspace.

This script allows you to create or update ZenML workspaces.It handles
authentication, workspace creation/updating, and monitoring the workspace
status until it becomes available.

Usage:

    python manage_workspace.py --workspace my-workspace --organization org-123
        --zenml-version 0.81.0 --docker-image my/custom:image

Environment Variables:
    Authentication (one of the following sets is required):
        CLOUD_STAGING_CLIENT_ID, CLOUD_STAGING_CLIENT_SECRET - Client credentials
        CLOUD_STAGING_CLIENT_TOKEN - Client token

    Workspace Configuration (can be overridden by function parameters):
        WORKSPACE_NAME_OR_ID - Name or ID of the workspace
        ORGANIZATION_ID - ID of the organization that owns the workspace
        ZENML_VERSION - Version of ZenML to use
        HELM_VERSION - Version of the Helm chart to use
        DOCKER_IMAGE - Docker image to use (format: repository:tag)
"""

import os
import time
from typing import Any, Dict, Optional

import requests


def _disect_docker_image_parts(docker_image: str) -> tuple[str, str]:
    """Get the image repository and tag from a Docker image.

    Args:
        docker_image: The Docker image to disect.

    Returns:
        The image repository and tag.
    """
    docker_image_parts = docker_image.split(":")
    if len(docker_image_parts) == 1:
        image_repository = docker_image_parts[0]
        image_tag = "latest"
    else:
        image_repository = docker_image_parts[0]
        image_tag = docker_image_parts[1]
    return image_repository, image_tag


def _get_headers(token: str) -> dict:
    """Get the headers for the staging API.

    Args:
        token: The access token for authentication.

    Returns:
        The headers as a dictionary.
    """
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}


def _build_configuration(
    zenml_version: str,
    docker_image: Optional[str] = None,
    helm_chart_version: Optional[str] = None,
) -> dict:
    """Build the configuration for the workspace.

    Args:
        zenml_version: The version of ZenML to use for the workspace.
        docker_image: The Docker image to use for the workspace.
        helm_version: The version of the Helm chart to use for the workspace.

    Returns:
        The configuration as a dictionary.
    """
    configuration: dict = {"version": zenml_version}

    if any([docker_image, helm_chart_version]):
        configuration["admin"] = {}

    if docker_image is not None:
        image_repository, image_tag = _disect_docker_image_parts(docker_image)
        configuration["admin"]["image_repository"] = image_repository
        configuration["admin"]["image_tag"] = image_tag

    if helm_chart_version is not None:
        configuration["admin"]["helm_chart_version"] = helm_chart_version

    return configuration


def get_token(client_id: str, client_secret: str) -> str:
    """Get an access token for the staging API.

    Args:
        client_id: The client ID for authentication.
        client_secret: The client secret for authentication.

    Returns:
        The access token as a string.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = "https://staging.cloudapi.zenml.io/auth/login"
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


def get_workspace(token: str, workspace_name_or_id: str) -> dict:
    """Get a workspace by name or ID.

    Args:
        token: The access token for authentication.
        workspace_name_or_id: The name or ID of the workspace to get.

    Returns:
        The workspace as a dictionary.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = (
        f"https://staging.cloudapi.zenml.io/workspaces/{workspace_name_or_id}"
    )

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
) -> dict:
    """Creating a workspace.

    Args:
        token: The access token for authentication.
        workspace_name: The name of the workspace to create.
        organization_id: The ID of the organization to create the workspace in.
        configuration: The configuration for the workspace.

    Returns:
        The created workspace as a dictionary.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = "https://staging.cloudapi.zenml.io/workspaces"

    data = {
        "name": workspace_name,
        "display_name": workspace_name,
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
    """Updating a workspace.

    Args:
        token: The access token for authentication.
        workspace_name_or_id: The name or ID of the workspace to update.
        configuration: The configuration for the workspace.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = (
        f"https://staging.cloudapi.zenml.io/workspaces/{workspace_name_or_id}"
    )

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


def main(
    workspace_name_or_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    zenml_version: Optional[str] = None,
    helm_version: Optional[str] = None,
    docker_image: Optional[str] = None,
) -> None:
    """Create or update a ZenML workspace and wait for it to become available.

    This function orchestrates the workspace management process:
    1. Authenticates with the ZenML Cloud API
    2. Checks if the workspace exists
    3. Creates or updates the workspace with the specified configuration
    4. Monitors the workspace status until it becomes available

    The function prioritizes parameters passed directly to it, falling back
    to environment variables if any parameters are not provided.

    Authentication is always done via environment variables.

    Args:
        workspace_name_or_id: The name or ID of the workspace to manage.
            Falls back to WORKSPACE_NAME_OR_ID environment variable.
        organization_id: The ID of the organization that owns the workspace.
            Falls back to ORGANIZATION_ID environment variable.
        zenml_version: The version of ZenML to use for the workspace.
            Falls back to ZENML_VERSION environment variable.
        helm_version: The version of the Helm chart to use for the workspace.
            Falls back to HELM_CHART_VERSION environment variable.
        docker_image: The Docker image to use for the workspace (format: repository:tag).
            Falls back to DOCKER_IMAGE environment variable.

    Raises:
        ValueError: If authentication credentials are not provided or are invalid.
        RuntimeError: If the workspace creation fails or times out.
    """
    # Parameters
    timeout = 600
    sleep_period = 20

    # Get credentials from environment variables
    client_id = os.environ.get("CLOUD_STAGING_CLIENT_ID")
    client_secret = os.environ.get("CLOUD_STAGING_CLIENT_SECRET")
    client_token = os.environ.get("CLOUD_STAGING_CLIENT_TOKEN")

    # Fetch token
    if client_token:
        if client_id or client_secret:
            raise ValueError(
                "client_id and client_secret must not be provided if client_token is provided"
            )

        token = client_token
    else:
        assert client_id is not None, "Client ID must be provided"
        assert client_secret is not None, "Client secret must be provided"

        token = get_token(client_id, client_secret)

    # Get organization and workspace from environment variables if not provided
    organization_id = organization_id or os.environ.get(
        "CLOUD_STAGING_GH_ACTIONS_ORGANIZATION_ID"
    )
    workspace_name_or_id = workspace_name_or_id or os.environ.get(
        "WORKSPACE_NAME_OR_ID"
    )

    # Check for missing required values
    assert workspace_name_or_id is not None, (
        "Workspace name or ID must be provided"
    )
    assert organization_id is not None, "Organization ID must be provided"

    # Get configuration from environment variables if not provided
    zenml_version = zenml_version or os.environ.get("ZENML_VERSION")
    helm_version = helm_version or os.environ.get("HELM_CHART_VERSION")
    docker_image = docker_image or os.environ.get("DOCKER_IMAGE")

    assert zenml_version is not None, "ZenML version must be provided"

    configuration = _build_configuration(
        zenml_version=zenml_version,
        docker_image=docker_image,
        helm_chart_version=helm_version,
    )

    # Get or create workspace
    exists = True
    try:
        workspace = get_workspace(token, workspace_name_or_id)
    except RuntimeError:
        workspace = create_workspace(
            token=token,
            workspace_name=workspace_name_or_id,
            organization_id=organization_id,
            configuration=configuration,
        )
        exists = False

    if exists:
        update_workspace(
            token=token,
            workspace_name_or_id=workspace["id"],
            configuration=configuration,
        )
    # Check the status using a deadline-based approach
    deadline = time.time() + timeout
    workspace = get_workspace(token, workspace_name_or_id)

    while workspace["status"] == "pending":
        print(f"Waiting... Current workspace status: {workspace['status']}.")

        if time.time() > deadline:
            raise RuntimeError(
                "Timed out! The workspace could be stuck in a `pending` state."
            )

        time.sleep(sleep_period)
        workspace = get_workspace(token, workspace_name_or_id)

    if workspace["status"] != "available":
        raise RuntimeError("Workspace creation failed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage a ZenML workspace.")
    parser.add_argument("--workspace", help="Workspace name or ID")
    parser.add_argument("--organization", help="Organization ID")
    parser.add_argument("--zenml-version", help="ZenML version")
    parser.add_argument("--helm-version", help="Helm chart version")
    parser.add_argument("--docker-image", help="Docker image")

    args = parser.parse_args()

    main(
        workspace_name_or_id=args.workspace,
        organization_id=args.organization,
        zenml_version=args.zenml_version,
        helm_version=args.helm_version,
        docker_image=args.docker_image,
    )
