---
description: Store secrets in GCP
---

The GCP secrets manager is a [secrets manager](./overview.md) flavor provided with
the ZenML `gcp` integration that uses [GCP](https://cloud.google.com/secret-manager)
to store secrets.

## When to use it

You should use the GCP secrets manager if:
* a component of your stack requires a secret for authentication or you want 
to use secrets inside your steps.
* you're already using GCP, especially if your orchestrator is running in GCP.
If you're using a different cloud provider, take a look at the other [secrets manager flavors](./overview.md#secrets-manager-flavors).

## How to deploy it

In order to use the GCP secrets manager, you need to enable it
[here](https://console.cloud.google.com/marketplace/product/google/secretmanager.googleapis.com).

## How to use it

To use the GCP secrets manager, we need:
* The ZenML `gcp` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install gcp
    ```
* The [GCP CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.
* The ID of the project in which you want to store secrets. Follow
[this guide](https://support.google.com/googleapi/answer/7014113?hl=en) to find your project ID.

We can then register the secrets manager and use it in our active stack:
```shell
zenml secrets-manager register <NAME> \
    --flavor=gcp_secrets_manager \
    --project_id=<PROJECT_ID>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

A concrete example of using the GCP secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/cloud_secrets_manager).

For more information and a full list of configurable attributes of the GCP secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.gcp.secrets_manager.gcp_secrets_manager.GCPSecretsManager).
