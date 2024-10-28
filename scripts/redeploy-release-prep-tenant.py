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

    if response.status_code != 200:
        raise requests.HTTPError("There was a problem fetching the token.")

    return response.json()["access_token"]


def update_tenant(token: str, tenant_id: str, new_version: str) -> None:
    """Update a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to update.
        new_version: New version of ZenML to be released.

    Raises:
        requests.HTTPError: If the API request fails.
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
                },
            },
        },
        "desired_state": "available",
    }

    response = requests.patch(
        url, json=data, headers=headers, params={"force": True}
    )
    if response.status_code != 200:
        raise requests.HTTPError("There was a problem updating the tenant.")


def get_tenant_status(token: str, tenant_id: str) -> str:
    """Get the current status of a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to check.

    Returns:
        The current status of the tenant as a string.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = f"https://staging.cloudapi.zenml.io/tenants/{tenant_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise requests.HTTPError("There was a problem fetching the status.")

    return response.json()["status"]


def main() -> None:
    """Main function to orchestrate the tenant management process.

    This function performs the following steps:
    1. Retrieves necessary environment variables.
    2. Gets an access token.
    3. Deactivates the specified tenant.
    4. Waits for the tenant to be fully deactivated.
    5. Redeploys the tenant.
    6. Waits for the tenant to be fully deployed.

    Raises:
        EnvironmentError: If required environment variables are missing.
        requests.HTTPError: If any API requests fail.
    """
    # Constants
    timeout = 600
    sleep_period = 20

    # Get environment variables
    client_id = os.environ.get("CLOUD_STAGING_CLIENT_ID")
    client_secret = os.environ.get("CLOUD_STAGING_CLIENT_SECRET")
    tenant_id = os.environ.get("RELEASE_TENANT_ID")
    new_version = os.environ.get("ZENML_NEW_VERSION")

    if not all([client_id, client_secret, tenant_id, new_version]):
        raise EnvironmentError("Missing required environment variables")

    # Get the token
    token = get_token(client_id, client_secret)
    print("Fetched the token.")

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
