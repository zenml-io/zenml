---
description: Learn how to manage and use service accounts and API keys .
icon: key
---

# Service Accounts

Service accounts in ZenML Pro provide a secure way to authenticate automated systems, CI/CD pipelines, and other non-interactive applications with your ZenML Pro organization. Unlike user accounts, service accounts are designed specifically for programmatic access and can be managed centrally through the Organization Settings interface.

## Accessing Service Account Management

To manage service accounts in your ZenML Pro organization, navigate to your ZenML Pro dashboard, click on **"Settings"** in the organization navigation menu and select **"Service Accounts"** from the settings sidebar. This is the main interface where you can perform all service account and API key operations.

![Service Accounts](.gitbook/assets/pro-service-accounts-01.png)

## Using Service Account API Keys

Once you have created a service account and API key, you can use them to authenticate to the ZenML Pro API and use it to programmatically manage your organization. You can also use the API key to access all the workspaces in your organization to e.g. run pipelines from the ZenML Python client.

### ZenML Pro API programmatic access

The API key can be used to authenticate to the ZenML Pro management REST API programmatically. There are two methods to do this - one is simpler but less secure, the other is secure and recommended but more complex:

{% tabs %} {% tab title="Direct API key authentication" %}
{% hint style="warning" %}
This approach, albeit simple, is not recommended because the long-lived API key is exposed with every API request, which makes it easier to be compromised. Use it only in low-risk circumstances.
{% endhint %}

To authenticate to the REST API, simply pass the API key directly in the `Authorization` header used with your API calls:

*   using curl:

    ```bash
    curl -H "Authorization: Bearer YOUR_API_KEY" https://cloudapi.zenml.io/users/me
    ```
*   using wget:

    ```bash
    wget -qO- --header="Authorization: Bearer YOUR_API_KEY" https://cloudapi.zenml.io/users/me
    ```
*   using python:

    ```python
    import requests

    response = requests.get(
      "https://cloudapi.zenml.io/users/me",
      headers={"Authorization": f"Bearer YOUR_API_KEY"}
    )
    print(response.json())
    ```
{% endtab %}

{% tab title="Token exchange authentication" %}
Reduce the risk of API key exposure by periodically exchanging the API key for a short-lived API token:

1. To obtain a short-lived API token using your API key, send a POST request to the `/auth/login` endpoint. Here are examples using common HTTP clients:
   *   using curl:

       ```bash
       curl -X POST -d "password=<YOUR_API_KEY>" https://cloudapi.zenml.io/auth/login
       ```
   *   using wget:

       ```bash
       wget -qO- --post-data="password=<YOUR_API_KEY>" \
           --header="Content-Type: application/x-www-form-urlencoded" \
           https://cloudapi.zenml.io/auth/login
       ```
   *   using python:

       ```python
       import requests
       import json

       response = requests.post(
           "https://cloudapi.zenml.io/auth/login",
           data={"password": "<YOUR_API_KEY>"},
           headers={"Content-Type": "application/x-www-form-urlencoded"}
       )

       print(response.json())
       ```

This will return a response like this (the short-lived API token is the `access_token` field):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MGJjZTg5NC1hN2VjLTRkOTYtYjE1Ny1kOTZkYWY5ZWM2M2IiLCJpc3MiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJhdWQiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJleHAiOjE3MTk0MDk0NjAsImFwaV9rZXlfaWQiOiIzNDkyM2U0NS0zMGFlLTRkMjctODZiZS0wZGRhNTdkMjA5MDcifQ.ByB1ngCPtBenGE6UugsWC6Blga3qPqkAiPJUSFDR-u4",
  "token_type": "bearer",
  "expires_in": 3600,
  "device_id": null,
  "device_metadata": null
}
```

2. Once you have obtained a short-lived API token, you can use it to authenticate your API requests by including it in the `Authorization` header. When the token expires, simply repeat the steps above to obtain a new short-lived API token. For example, you can use the following command to check your current user:
   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_API_TOKEN" https://cloudapi.zenml.io/users/me
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_API_TOKEN" https://cloudapi.zenml.io/users/me
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
           "https://cloudapi.zenml.io/users/me",
           headers={"Authorization": f"Bearer {YOUR_API_TOKEN}"}
       )

       print(response.json())
       ```
{% endtab %}
{% endtabs %}

See the [API documentation](https://docs.zenml.io/api-reference/pro-api/getting-started) for detailed information on programmatic access patterns.

It is also possible to authenticate as the service account using the OpenAPI UI available at https://cloudapi.zenml.io:

![OpenAPI UI authentication](.gitbook/assets/pro-service-account-auth-01.png)

The session token is stored as a cookie, which essentially authenticates your entire OpenAPI UI session. Not only that, but you can now open https://cloud.zenml.io and navigate your organization and its resources as the service account.

![ZenML Pro UI authentication](.gitbook/assets/pro-service-account-auth-02.png)

### Workspace access

You can also use the ZenML Pro API key to access all the workspaces in your organization:

* with environment variables:

```bash
# set this to the ZenML Pro workspace URL
export ZENML_STORE_URL=https://your-org.zenml.io
export ZENML_STORE_API_KEY=<your-api-key>
# optional, for self-hosted ZenML Pro API servers, set this to the ZenML Pro
# API URL, if different from the default https://cloudapi.zenml.io
export ZENML_PRO_API_URL=https://...
```

* with the CLI:

```bash
zenml login <your-workspace-name> --api-key
# You will be prompted to enter your API key
```

#### ZenML Pro Workspace API programmatic access

Similar to the ZenML Pro API programmatic access, the API key can be used to authenticate to the ZenML Pro workspace REST API programmatically. This is no different from [using the OSS API key to authenticate to the OSS workspace REST API programmatically](https://docs.zenml.io/api-reference/oss-api/getting-started#using-a-service-account-and-an-api-key). There are two methods to do this - one is simpler but less secure, the other is secure and recommended but more complex:

{% tabs %} {% tab title="Direct Pro API key authentication" %}
{% hint style="warning" %}
This approach, albeit simple, is not recommended because the long-lived Pro API key is exposed with every API request, which makes it easier to be compromised. Use it only in low-risk circumstances.
{% endhint %}

Use the Pro API key directly to authenticate your API requests by including it in the `Authorization` header. For example, you can use the following command to check your current workspace user:

*   using curl:

    ```bash
    curl -H "Authorization: Bearer YOUR_API_KEY" https://your-workspace-url/api/v1/current-user
    ```
*   using wget:

    ```bash
    wget -qO- --header="Authorization: Bearer YOUR_API_KEY" https://your-workspace-url/api/v1/current-user
    ```
*   using python:

    ```python
    import requests

    response = requests.get(
        "https://your-workspace-url/api/v1/current-user",
        headers={"Authorization": f"Bearer {YOUR_API_KEY}"}
    )

    print(response.json())
    ```
{% endtab %}

{% tab title="Token exchange authentication" %}
Reduce the risk of Pro API key exposure by periodically exchanging the Pro API key for a short-lived workspace API token.

1. To obtain a short-lived workspace API token using your Pro API key, send a POST request to the `/api/v1/login` endpoint. Here are examples using common HTTP clients:
   *   using curl:

       ```bash
       curl -X POST -d "password=<YOUR_API_KEY>" https://your-workspace-url/api/v1/login
       ```
   *   using wget:

       ```bash
       wget -qO- --post-data="password=<YOUR_API_KEY>" \
           --header="Content-Type: application/x-www-form-urlencoded" \
           https://your-workspace-url/api/v1/login
       ```
   *   using python:

       ```python
       import requests
       import json

       response = requests.post(
           "https://your-workspace-url/api/v1/login",
           data={"password": "<YOUR_API_KEY>"},
           headers={"Content-Type": "application/x-www-form-urlencoded"}
       )

       print(response.json())
       ```

This will return a response like this (the workspace API token is the `access_token` field):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MGJjZTg5NC1hN2VjLTRkOTYtYjE1Ny1kOTZkYWY5ZWM2M2IiLCJpc3MiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJhdWQiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJleHAiOjE3MTk0MDk0NjAsImFwaV9rZXlfaWQiOiIzNDkyM2U0NS0zMGFlLTRkMjctODZiZS0wZGRhNTdkMjA5MDcifQ.ByB1ngCPtBenGE6UugsWC6Blga3qPqkAiPJUSFDR-u4",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": null,
  "scope": null
}
```

2. Once you have obtained a short-lived workspace API token, you can use it to authenticate your API requests by including it in the `Authorization` header. When the short-lived workspace API token expires, simply repeat the steps above to obtain a new one. For example, you can use the following command to check your current workspace user:
   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_API_TOKEN" https://your-workspace-url/api/v1/current-user
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_API_TOKEN" https://your-workspace-url/api/v1/current-user
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
           "https://your-workspace-url/api/v1/current-user",
           headers={"Authorization": f"Bearer {YOUR_API_TOKEN}"}
       )

       print(response.json())
       ```
{% endtab %}
{% endtabs %}

## Service Account Operations

### Managing Service Account Roles and Permissions

Service accounts are no different from regular users in that they can be assigned different [Organization, Workspace and Project roles](roles.md) to control their access to different parts of the organization and they can be organized into [teams](teams.md). They are marked as "BOT" in the UI, to clearly identify them as non-human users.

![Service account Organization roles](.gitbook/assets/pro-service-accounts-13.png) ![Service account Workspace roles](.gitbook/assets/pro-service-accounts-14.png)

### Activating and Deactivating Service Accounts

Service account activation controls whether the account can be used for authentication. Deactivating a service account immediately prevents all associated API keys from working.

{% hint style="danger" %}
**Immediate Effect**

Deactivating a service account has immediate effect on all ZenML Pro API calls using any of its API keys. Ensure you coordinate with your team before deactivating production service accounts.
{% endhint %}

{% hint style="warning" %}
**Delayed workspace token effect**

Short-lived API tokens associated with the deactivated service account issued for workspaces in your organization may still be valid for up to one hour after the service account is deactivated.
{% endhint %}

### Deleting a Service Account

Deleting a service account permanently removes it and all associated API keys from your organization.

{% hint style="warning" %}
**Delayed workspace token effect**

Short-lived API tokens associated with the deleted service account issued for workspaces in your organization may still be valid for up to one hour after the service account is deleted.
{% endhint %}

## API Key Management

API keys are the credentials used by applications to authenticate as a service account. Each service account can have multiple API keys, allowing for different access patterns. When you create a new service account, you have the option to automatically create a default API key for it.

### Creating an API Key

{% hint style="danger" %}
**One-Time Display**

The API key value is only shown once during creation and cannot be retrieved later. If you lose an API key, you must create a new one or rotate the existing key.
{% endhint %}

### Activating and Deactivating API Keys

Individual API keys can be activated or deactivated independently of the service account status.

{% hint style="warning" %}
**Delayed workspace token effect**

Short-lived API tokens associated with the deactivated API key issued for workspaces in your organization may still be valid for up to one hour after the API key is deactivated.
{% endhint %}

### Rotating API Keys

API key rotation creates a new key value while optionally preserving the old key for a transition period. This is essential for maintaining security without service interruption.

{% hint style="info" %}
**Zero-Downtime Rotation**

By setting a retention period, you can update your applications to use the new API key while the old key remains functional. This enables zero-downtime key rotation for production systems.
{% endhint %}

### Deleting API Keys

{% hint style="warning" %}
**Delayed workspace token effect**

Short-lived API tokens associated with the deleted API key issued for workspaces in your organization may still be valid for up to one hour after the API key is deleted.
{% endhint %}

## Security Best Practices

### Key Management

* **Regular Rotation**: Rotate API keys regularly (recommended: every 90 days for production keys)
* **Principle of Least Privilege**: Create separate service accounts for different purposes rather than sharing keys
* **Secure Storage**: Store API keys in secure credential management systems, never in code repositories
* **Monitor Usage**: Regularly review the "last used" timestamps to identify unused keys

### Access Control

* **Descriptive Naming**: Use clear, descriptive names for service accounts and API keys to track their purposes
* **Documentation**: Maintain documentation of which systems use which service accounts
* **Regular Audits**: Periodically review and clean up unused service accounts and API keys

### Operational Security

* **Immediate Deactivation**: Deactivate service accounts and API keys immediately when they're no longer needed
* **Incident Response**: Have procedures in place to quickly rotate or deactivate compromised keys
* **Team Coordination**: Coordinate with your team before making changes to production service accounts


## Migration of workspace level service accounts

Workspace-level service accounts and API keys in ZenML Pro are deprecated. Existing workspace-level API keys may continue to authenticate temporarily for compatibility, but workloads that keep using workspace-level service account API keys will lose access during a future workspace upgrade. Please migrate them to organization-level service accounts as soon as possible.

The reason for this deprecation is that workspace-level service accounts and API keys cannot be subjected to RBAC rules and therefore always have full access to the workspace.

Use ZenML Pro organization service accounts instead. They are managed centrally in the ZenML Pro control plane and can be used to authenticate both to the ZenML Pro API and to the Workspace API for the workspaces in your organization.

To migrate automation that still uses a workspace-level service account API key, follow these steps:

1. Create a ZenML Pro organization service account in **Organization** > **Settings** > **Service Accounts**. Use the exact same username as the old workspace-level service account. This allows ZenML Pro to adopt resources owned by the old workspace-level service account and preserve lineage/history under the migrated organization-level service account. Be aware that the organization-level service account is shared across all workspaces in the organization.
2. [Assign Organization and Workspace roles](roles.md) to the new service account. To preserve the same unrestricted permissions that the workspace-level service account currently has but limited to the affected workspace, grant the **Organization Member** role at the organization level and the **Workspace Admin** role in the affected workspace. For better security, we strongly recommend making full use of ZenML Pro RBAC and granting only the specific roles and permissions that the service account actually needs.
3. Create an API key for the new organization-level service account and update your automation, CI/CD jobs, and pipeline workloads to use that key instead of the old workspace-level API key.

You can keep using the workspace URL as the ZenML store URL:

   ```bash
   export ZENML_STORE_URL=https://your-workspace-url
   export ZENML_STORE_API_KEY=<your-zenml-pro-organization-api-key>
   ```

For self-hosted ZenML Pro API servers, also set the ZenML Pro API URL:

   ```bash
   export ZENML_PRO_API_URL=https://your-pro-api-url
   ```

4. Run the affected workloads once to verify that they authenticate successfully with the organization-level service account.
5. If the migration is successful and the correct username is used at step 1, the old workspace-level service account is automatically "adopted" by the new organization-level service account and will no longer be listed in the workspace settings.
6. For workspace-level service accounts that are no longer used, deactivate them or delete them. Deactivation immediately prevents their API keys from being used. Deletion can fail if the service account already owns resources such as pipeline runs; in that case, deactivate the service account instead.

## Troubleshooting

### Common Issues

**API Key Not Working**

* Verify the service account is active
* Verify the specific API key is active
* Check that the API key hasn't expired (if using rotation with retention)
* Ensure the API key is correctly formatted in your environment variables

**Cannot Delete Service Account**

* Verify you have the necessary permissions in the organization

**API Key Creation Failed**

* Ensure you have write permissions in the organization
* Check that the service account is active
* Verify the API key name doesn't conflict with existing keys

{% hint style="info" %}
**Need Help?**

If you encounter issues with service account management, check the ZenML Pro documentation or contact your organization administrator for assistance with permissions and access control.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
