---
description: >-
  Connect to the ZenML server using a temporary API token.
---

# Connect with an API Token

API tokens provide a way to authenticate with the ZenML server for temporary automation tasks. These tokens are scoped to your user account and are valid for a maximum of 1 hour.

## Generating an API Token

To generate a new API token:

1. Navigate to the server's Settings page in your ZenML dashboard (or the workspace's Settings page in your ZenML Pro dashboard)
2. Select "API Tokens" from the left sidebar

    ![API Tokens](../../../.gitbook/assets/zenml-oss-api-token-01.png)

3. Click the "Create new token" button. Once generated, you'll see a dialog showing your new API token. 

    ![API Tokens](../../../.gitbook/assets/zenml-oss-api-token-02.png)

## Programmatic access with API tokens

You can use the generated API tokens for programmatic access to the ZenML server's REST API. This is the quickest way to access the ZenML API programmatically when you're not using the ZenML CLI or Python client and you don't want to set up a service account.

Accessing the API with this method is thoroughly documented in the [API reference section](../../../reference/api-reference.md#using-a-short-lived-api-token).


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


