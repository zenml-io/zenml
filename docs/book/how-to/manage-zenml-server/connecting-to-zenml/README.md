---
icon: globe-pointer
description: Various means of connecting to ZenML.
---

# Connect to a server

Once [ZenML is deployed](../../../getting-started/deploying-zenml/README.md), there are various ways to connect to it.

## Choose how to connect

Use this quick guide to pick the right method based on your context:

| Context | Use | Credentials | Docs |
|---|---|---|---|
| You are a human using the CLI and browser | Interactive login (device flow) | Your user session (24h/30d) | [Connect with your user](./connect-in-with-your-user-interactive.md) |
| Script/notebook needs to make quick API calls to an OSS server | Service account + API key | Long‑lived API key | [Connect with a service account](./connect-with-a-service-account.md) |
| Script/notebook needs to make quick API calls to a ZenML Pro workspace | ZenML Pro Personal Access Token | Long‑lived PAT | [Connect with a personal access token](./connect-with-a-pat.md) |
| CI/CD or long‑lived automation calling an OSS server | Service account + API key | Long‑lived API key | [Connect with a service account](./connect-with-a-service-account.md) |
| CI/CD or long‑lived automation calling a ZenML Pro workspace | ZenML Pro API service account + API key | Long‑lived API key | [Connect with a ZenML Pro service account](https://docs.zenml.io/api-reference/pro-api/getting-started#programmatic-access-with-service-accounts-and-api-keys) |
| CI/CD or long‑lived automation calling the ZenML Pro management API (`cloudapi.zenml.io`) | ZenML Pro service account + API key | Long-lived API key | [Connect with a ZenML Pro service account](https://docs.zenml.io/api-reference/pro-api/getting-started#programmatic-access-with-service-accounts-and-api-keys) |

{% hint style="warning" %}
Which base URL should you call?

- Workspace/OSS API: your server or workspace URL (e.g., `https://<workspace-id>.zenml.io`).
- ZenML Pro management API: `https://cloudapi.zenml.io`.

In ZenML Pro, use Personal Access Tokens or organization‑level service accounts and API keys (workspace‑level service accounts are deprecated). PATs and org‑level service accounts can be used for both the Workspace API and the Pro management API. See [ZenML Pro Personal Access Tokens](https://docs.zenml.io/pro/core-concepts/personal-access-tokens) and [ZenML Pro Organization Service Accounts](https://docs.zenml.io/pro/core-concepts/service-accounts).
{% endhint %}

## Common pitfalls

- 401 Unauthorized: verify you’re using the correct base URL, the token hasn’t expired, and the header is `Authorization: Bearer <token>`.
- Automation fails after 1 hour: check the expiration date of the PAT or API key and rotate it if it has expired.
- Can’t find Run Template endpoints: they exist on the Workspace/OSS API, not on `cloudapi.zenml.io`.