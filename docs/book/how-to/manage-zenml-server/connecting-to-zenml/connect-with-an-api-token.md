---
description: >-
  Connect to the ZenML server using a temporary API token.
---

# Connect with an API Token

API tokens provide a way to authenticate with the ZenML server for temporary automation tasks. These tokens are scoped to the user account or service account that is currently logged in and are short-lived: they have a configurable expiration time (default 1 hour) and need to be renewed periodically.

## Generating an API Token in the ZenML UI

To generate a new API token through the ZenML UI:

1. Navigate to the server's Settings page in your ZenML dashboard (or the workspace's Settings page in your ZenML Pro dashboard)
2. Select "API Tokens" from the left sidebar

    ![API Tokens](../../../.gitbook/assets/zenml-oss-api-token-01.png)

3. Click the "Create new token" button. Once generated, you'll see a dialog showing your new API token. 

    ![API Tokens](../../../.gitbook/assets/zenml-oss-api-token-02.png)

The UI generated tokens have a fixed expiration time of 1 hour.

## Generating an API Token with the CLI

To generate a new API token with the CLI, run the `zenml token` command. This will print the token to the console.

```bash
zenml token
```

With the CLI, you can control the expiration time of the token by setting the `--expires-in` option. The default expiration time is 1 hour. The ZenML server also imposes a configurable maximum expiration time with a default value of 7 days. You can tweak the maximum expiration time in the ZenML server configuration to accommodate larger values (set the `ZENML_SERVER_GENERIC_API_TOKEN_MAX_LIFETIME` server environment variable), although this is not recommended for security reasons.

## Programmatic access with API tokens

You can use the generated API tokens for programmatic access to the ZenML server's REST API (OSS server or Workspace API). This is the quickest way to access the ZenML API programmatically when you're not using the ZenML CLI or Python client and you don't want to set up a service account.

Accessing the API with this method is thoroughly documented in the [API reference section](https://docs.zenml.io/api-reference/oss-api/getting-started#using-a-short-lived-api-token).

{% hint style="info" %}
Using the ZenML Pro management API (`cloudapi.zenml.io`)? Generate organization‑scoped API tokens in the Pro dashboard instead. See [Pro API Getting Started](https://docs.zenml.io/api-reference/pro-api/getting-started#programmatic-access-with-api-tokens).
{% endhint %}