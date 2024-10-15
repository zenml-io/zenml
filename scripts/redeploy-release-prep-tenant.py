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


def deactivate_tenant(token: str, tenant_id: str) -> None:
    """Deactivate a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to deactivate.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = f"https://staging.cloudapi.zenml.io/tenants/{tenant_id}/deactivate"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    response = requests.patch(url, headers=headers)

    if response.status_code != 200:
        raise requests.HTTPError(
            "There was a problem deactivating the tenant."
        )


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


def redeploy_tenant(token: str, tenant_id: str) -> None:
    """Redeploy a specific tenant.

    Args:
        token: The access token for authentication.
        tenant_id: The ID of the tenant to redeploy.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    url = f"https://staging.cloudapi.zenml.io/tenants/{tenant_id}/deploy"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    response = requests.patch(url, headers=headers)

    if response.status_code != 200:
        raise requests.HTTPError("There was a problem redeploying the tenant.")


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
    # Get environment variables
    client_id = os.environ.get("CLOUD_STAGING_CLIENT_ID")
    client_secret = os.environ.get("CLOUD_STAGING_CLIENT_SECRET")
    tenant_id = os.environ.get("RELEASE_TENANT_ID")

    if not all([client_id, client_secret, tenant_id]):
        raise EnvironmentError("Missing required environment variables")

    # Get the token
    token = get_token(client_id, client_secret)
    print("Fetched the token.")

    # Deactivate the tenant
    status = get_tenant_status(token, tenant_id)
    if status == "available":
        deactivate_tenant(token, tenant_id)
        print("Tenant deactivation initiated.")

    # Wait until it's deactivated
    time.sleep(10)

    status = get_tenant_status(token, tenant_id)
    while status == "pending":
        print(f"Waiting... Current tenant status: {status}.")
        time.sleep(20)
        status = get_tenant_status(token, tenant_id)

    if status != "deactivated":
        raise RuntimeError("Tenant deactivation failed.")
    print("Tenant deactivated.")

    # Redeploy the tenant
    redeploy_tenant(token, tenant_id)
    print("Tenant redeployment initiated.")

    # Wait until it's deployed
    time.sleep(10)

    status = get_tenant_status(token, tenant_id)
    while status == "pending":
        print(f"Waiting... Current tenant status: {status}.")
        time.sleep(20)
        status = get_tenant_status(token, tenant_id)

    if status != "available":
        raise RuntimeError("Tenant redeployment failed.")
    print("Tenant redeployed.")


if __name__ == "__main__":
    main()
