---
icon: key
description: >-
  Learn how to manage and use Personal Access Tokens.
---

# ZenML Pro Personal Access Tokens

Personal Access Tokens (PATs) in ZenML Pro provide a secure way to 
authenticate your user account programmatically with the ZenML Pro API and 
workspaces. PATs are associated with your personal user account and inherit 
your full permissions within all organizations you are a member of.

{% hint style="warning" %}
**Security Consideration**

Personal Access Tokens inherit your complete user permissions and should be 
used with care. For automation tasks like CI/CD pipelines, we strongly 
recommend using [service accounts](./service-accounts.md) instead, following the
principle of least privilege. Service accounts allow you to grant only the specific
permissions needed for automated workflows.
{% endhint %}

{% hint style="info" %}
**Account-Level Management**

Personal Access Tokens in ZenML Pro are tied to your user account and are not scoped to a specific organization. This means that you can use the same PAT to access all organizations your user account is a member of.
{% endhint %}

## Accessing Personal Access Token Management

To manage Personal Access Tokens for your user account in ZenML Pro, navigate to your ZenML Pro dashboard, click on your profile picture in the top right corner, then select **"Settings"** and select **"Access Tokens"** from the settings sidebar. This is the main interface where you can perform all Personal Access Token operations.

![Personal Access Tokens](../../.gitbook/assets/pro-personal-access-tokens-01.png)


## Using Personal Access Tokens

Once you have created a Personal Access Token, you can use it to 
authenticate to the ZenML Pro API and programmatically manage your 
organization. You can also use the PAT to access all the workspaces in your 
organization to e.g. run pipelines from the ZenML Python client.

### ZenML Pro API programmatic access

The PAT can be used to authenticate to the ZenML Pro management REST API 
programmatically. There are two methods to do this - one is simpler but less 
secure, the other is secure and recommended but more complex:

{% tabs %}
{% tab title="Direct PAT authentication" %}

{% hint style="warning" %}
This approach, albeit simple, is not recommended because the long-lived PAT 
is exposed with every API request, which makes it easier to be compromised. 
Use it only in low-risk circumstances.
{% endhint %}

To authenticate to the REST API, simply pass the PAT directly in the 
`Authorization` header used with your API calls:

   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_PAT" https://cloudapi.zenml.io/users/me
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_PAT" https://cloudapi.zenml.io/users/me
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
         "https://cloudapi.zenml.io/users/me",
         headers={"Authorization": f"Bearer YOUR_PAT"}
       )
       print(response.json())
       ```


{% endtab %}

{% tab title="Token exchange authentication" %}

Reduce the risk of PAT exposure by periodically exchanging the PAT for a 
short-lived API token:

1. To obtain a short-lived API token using your PAT, send a POST request to the 
   `/auth/login` endpoint. Here are examples using common HTTP clients:
   *   using curl:

       ```bash
       curl -X POST -d "password=<YOUR_PAT>" https://cloudapi.zenml.io/auth/login
       ```
   *   using wget:

       ```bash
       wget -qO- --post-data="password=<YOUR_PAT>" \
           --header="Content-Type: application/x-www-form-urlencoded" \
           https://cloudapi.zenml.io/auth/login
       ```
   *   using python:

       ```python
       import requests
       import json

       response = requests.post(
           "https://cloudapi.zenml.io/auth/login",
           data={"password": "<YOUR_PAT>"},
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

2. Once you have obtained a short-lived API token, you can use it to authenticate 
   your API requests by including it in the `Authorization` header. When the 
   short-lived API token expires, simply repeat the steps above to obtain a
   new short-lived API token. For example, you can use the following command to check your current user:
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

### Workspace access

You can also use your Personal Access Token to access all the workspaces in 
your organization:

* with environment variables:
```bash
# set this to the ZenML Pro workspace URL
export ZENML_STORE_URL=https://your-org.zenml.io
export ZENML_STORE_API_KEY=<your-pat>
# optional, for self-hosted ZenML Pro API servers, set this to the ZenML Pro
# API URL, if different from the default https://cloudapi.zenml.io
export ZENML_PRO_API_URL=https://...
```

* with the CLI:
```bash
zenml login <your-workspace-name> --api-key
# You will be prompted to enter your PAT
```

#### ZenML Pro Workspace API programmatic access

Similar to the ZenML Pro API programmatic access, the PAT can be used to 
authenticate to the ZenML Pro workspace REST API programmatically. This is 
no different from [using the OSS API key to authenticate to the OSS workspace REST API programmatically](https://docs.zenml.io/api-reference/oss-api/getting-started#using-a-service-account-and-an-api-key). 
There are two methods to do this - one is simpler but less secure, the other 
is secure and recommended but more complex:

{% tabs %}
{% tab title="Direct PAT authentication" %}

{% hint style="warning" %}
This approach, albeit simple, is not recommended because the long-lived PAT 
is exposed with every API request, which makes it easier to be compromised. 
Use it only in low-risk circumstances.
{% endhint %}

Use the PAT directly to authenticate your API requests by including it in 
the `Authorization` header. For example, you can use the following command 
to check your current workspace user:

   *   using curl:

       ```bash
       curl -H "Authorization: Bearer YOUR_PAT" https://your-workspace-url/api/v1/current-user
       ```
   *   using wget:

       ```bash
       wget -qO- --header="Authorization: Bearer YOUR_PAT" https://your-workspace-url/api/v1/current-user
       ```
   *   using python:

       ```python
       import requests

       response = requests.get(
           "https://your-workspace-url/api/v1/current-user",
           headers={"Authorization": f"Bearer {YOUR_PAT}"}
       )

       print(response.json())
       ```

{% endtab %}

{% tab title="Token exchange authentication" %}

Reduce the risk of PAT exposure by periodically exchanging the PAT for a 
short-lived workspace API token.

1. To obtain a short-lived workspace API token using your PAT, send a POST 
   request to the `/api/v1/login` endpoint. Here are examples using common 
   HTTP clients:
   *   using curl:

       ```bash
       curl -X POST -d "password=<YOUR_PAT>" https://your-workspace-url/api/v1/login
       ```
   *   using wget:

       ```bash
       wget -qO- --post-data="password=<YOUR_PAT>" \
           --header="Content-Type: application/x-www-form-urlencoded" \
           https://your-workspace-url/api/v1/login
       ```
   *   using python:

       ```python
       import requests
       import json

       response = requests.post(
           "https://your-workspace-url/api/v1/login",
           data={"password": "<YOUR_PAT>"},
           headers={"Content-Type": "application/x-www-form-urlencoded"}
       )

       print(response.json())
       ```

This will return a response like this (the short-lived workspace API token is the 
`access_token` field):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MGJjZTg5NC1hN2VjLTRkOTYtYjE1Ny1kOTZkYWY5ZWM2M2IiLCJpc3MiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJhdWQiOiJmMGQ5NjI1Ni04YmQyLTQxZDctOWVjZi0xMmYwM2JmYTVlMTYiLCJleHAiOjE3MTk0MDk0NjAsImFwaV9rZXlfaWQiOiIzNDkyM2U0NS0zMGFlLTRkMjctODZiZS0wZGRhNTdkMjA5MDcifQ.ByB1ngCPtBenGE6UugsWC6Blga3qPqkAiPJUSFDR-u4",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": null,
  "scope": null
}
```

2. Once you have obtained a short-lived workspace API token, you can use it to 
   authenticate your API requests by including it in the `Authorization` 
   header. When the short-lived workspace API token expires, simply repeat the 
   steps above to obtain a new one. For example, you can use the following command to check your current workspace user:
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


## Personal Access Token Operations

Personal Access Tokens are the credentials used to authenticate your user 
account programmatically. You can have multiple PATs, allowing for different access patterns for various tools and applications.


### Creating a Personal Access Token


{% hint style="danger" %}
**One-Time Display**

The Personal Access Token value is only shown once during creation and 
cannot be retrieved later. If you lose a PAT, you must create a new one or 
rotate the existing PAT.
{% endhint %}

### Activating and Deactivating Personal Access Tokens

Individual Personal Access Tokens can be activated or deactivated as needed.

{% hint style="warning" %}
**Delayed workspace-level effect**

Temporary API tokens associated with the deactivated PAT issued for workspaces in 
your organization may still be valid for up to one hour after the PAT is 
deactivated.
{% endhint %}

### Rotating Personal Access Tokens

PAT rotation creates a new token value while optionally preserving the old 
token for a transition period. This is essential for maintaining security 
without service interruption.

{% hint style="info" %}
**Zero-Downtime Rotation**

By setting a retention period, you can update your applications to use the 
new PAT while the old token remains functional. This enables zero-downtime 
token rotation for production systems.
{% endhint %}

### Deleting Personal Access Tokens

{% hint style="warning" %}
**Delayed workspace-level effect**

Temporary API tokens associated with the deleted PAT issued for workspaces in your 
organization may still be valid for up to one hour after the PAT is deleted.
{% endhint %}

## Security Best Practices

### Token Management
- **Regular Rotation**: Rotate PATs regularly (recommended: every 90 days)
- **Set the Expiration Date**: Set an expiration date for PATs to automatically revoke them after a certain period of time, especially if you are only planning on using them for a short period of time.
- **Use Service Accounts for CI/CD**: For automated workflows and CI/CD 
  pipelines, use [service accounts](./service-accounts.md) instead of PATs. This follows the principle of least privilege by granting only necessary permissions 
  rather than your full user permissions.
- **Secure Storage**: Store PATs in secure credential management systems, 
  never in code repositories
- **Monitor Usage**: Regularly review the "last used" timestamps to 
  identify unused tokens

### Access Control
- **Descriptive Naming**: Use clear, descriptive names for PATs to track 
  their purposes (e.g., "work-laptop", "home-jupyter")
- **Documentation**: Maintain documentation of which systems and tools use 
  which tokens
- **Regular Audits**: Periodically review and clean up unused PATs

### Operational Security
- **Immediate Deactivation**: Deactivate PATs immediately when they're no 
  longer needed or if a device is lost or compromised
- **Incident Response**: Have procedures in place to quickly rotate or 
  deactivate compromised tokens
- **Minimize Token Scope**: Only create PATs when necessary for 
  programmatic access; use regular login for interactive sessions

## Troubleshooting

### Common Issues

**Personal Access Token Not Working**
- Verify the PAT is active
- Check that the PAT hasn't expired (if using rotation with retention)
- Ensure the PAT is correctly formatted in your environment variables
- Verify your user account has the necessary permissions

**Personal Access Token Creation Failed**
- Ensure you have permission to create PATs in the organization
- Verify the PAT name doesn't conflict with existing tokens
- Check with your organization administrator if PAT creation is restricted

{% hint style="info" %}
**Need Help?**

If you encounter issues with Personal Access Tokens, check the ZenML Pro 
documentation or contact your organization administrator for assistance with 
permissions and access control.
{% endhint %}