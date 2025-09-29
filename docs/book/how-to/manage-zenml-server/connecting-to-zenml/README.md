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
| Script/notebook needs quick API calls to a workspace or OSS server | Temporary API token (1h) | User-scoped token | [Connect with an API token](./connect-with-an-api-token.md) |
| CI/CD or long‑lived automation calling a workspace or OSS server | Service account + API key | Long‑lived API key issuing short‑lived tokens | [Connect with a service account](./connect-with-a-service-account.md) |
| Managing orgs/workspaces/users via Pro management API (`cloudapi.zenml.io`) | ZenML Pro API token (1h) or org service account + API key | Org-scoped token or API key | See Pro API [Getting Started](https://docs.zenml.io/api-reference/pro-api/getting-started#programmatic-access-with-api-tokens) |

{% hint style="warning" %}
Which base URL should you call?

- Workspace/OSS API: your server or workspace URL (e.g., `https://<workspace-id>.zenml.io`).
- ZenML Pro management API: `https://cloudapi.zenml.io`.

In ZenML Pro, use organization‑level service accounts and API keys (workspace‑level service accounts are deprecated). Org‑level service accounts can be used for both the Workspace API and the Pro management API. Alternatively, you can use short‑lived user API tokens. See [ZenML Pro Organization Service Accounts](https://docs.zenml.io/pro/core-concepts/service-accounts).
{% endhint %}

## Common pitfalls

- 401 Unauthorized: verify you’re using the correct base URL, the token hasn’t expired, and the header is `Authorization: Bearer <token>`.
- Automation fails after 1 hour: switch from temporary API tokens to service accounts + API keys.
- Can’t find Run Template endpoints: they exist on the Workspace/OSS API, not on `cloudapi.zenml.io`.