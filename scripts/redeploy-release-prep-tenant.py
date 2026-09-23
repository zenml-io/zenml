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
"""Deactivates and redeploys the release prep tenant with a new server image."""

import os
import time

import requests


def get_token(api_key: str) -> str:
    """Exchange a ZenML Pro API key for an access token.

    Args:
        api_key: The ZenML Pro service account API key.

    Returns:
        The short-lived access token.

    Raises:
        RuntimeError: If the API request fails or returns no access token.
    """
    url = "https://staging.cloudapi.zenml.io/auth/login"
    response = requests.post(
        url,
        data={"password": api_key},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )

    access_token = response.json().get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Login response did not contain an access token.")
    return access_token


def update_tenant(token: str, tenant_id: str, new_version: str) -> None:
    """Update a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to update.
        new_version: New version of ZenML to be released.

    Raises:
        RuntimeError: If the API request fails.
    """
    url = f"https://staging.cloudapi.zenml.io/tenants/{tenant_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }

    data = {
        "zenml_service": {
            "configuration": {
                "admin": {
                    "image_repository": "zenmldocker/prepare-release",
                    "image_tag": f"server-{new_version}",
                    "environment_vars": {
                        "ZENML_STORE_BACKUP_STRATEGY": "in-memory",
                    },
                    "features": {
                        "schedules": {
                            "enabled": False,
                        },
                        "resource_pools": {
                            "enabled": False,
                        },
                    },
                },
            },
        },
        "desired_state": "available",
    }

    response = requests.patch(
        url, json=data, headers=headers, params={"force": True}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )


def get_tenant_status(token: str, tenant_id: str) -> str:
    """Get the current status of a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to check.

    Returns:
        The current status of the tenant as a string.

    Raises:
        RuntimeError: If the API request fails.
    """
    url = f"https://staging.cloudapi.zenml.io/tenants/{tenant_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"Request failed with response content: {response.text}"
        )

    workspace_status = response.json().get("status")
    if not isinstance(workspace_status, str):
        raise RuntimeError("Workspace response did not contain a status.")
    return workspace_status


def main() -> None:
    """Main function to orchestrate the tenant management process.

    This function performs the following steps:
    1. Retrieves necessary environment variables.
    2. Exchanges a service account API key for an access token.
    3. Redeploys the specified tenant.
    4. Waits for the tenant to be fully deployed.

    Raises:
        EnvironmentError: If required environment variables are missing.
        RuntimeError: If an API request fails or the redeployment times out.
    """
    # Constants
    timeout = 600
    sleep_period = 20

    # Get environment variables
    api_key = os.environ.get("ZENML_PRO_API_KEY")
    tenant_id = os.environ.get("RELEASE_TENANT_ID")
    new_version = os.environ.get("ZENML_NEW_VERSION")

    if not api_key or not tenant_id or not new_version:
        raise EnvironmentError("Missing required environment variables")

    token = get_token(api_key)
    print("Fetched the access token.")

    # Update the tenant
    update_tenant(token, tenant_id, new_version)
    print("Tenant updated.")

    # Check the status
    status = get_tenant_status(token, tenant_id)
    while status == "pending":
        print(f"Waiting... Current tenant status: {status}.")
        time.sleep(sleep_period)
        status = get_tenant_status(token, tenant_id)

        timeout -= sleep_period
        if timeout <= 0:
            raise RuntimeError(
                "Timed out! The tenant could be stuck in a `pending` state."
            )

    if status != "available":
        raise RuntimeError("Tenant redeployment failed.")


if __name__ == "__main__":
    main()
