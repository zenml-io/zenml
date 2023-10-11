---
description: Storing secrets in GCP.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Google Cloud Secrets Manager

The GCP secrets manager is a [secrets manager](secrets-managers.md) flavor provided with the ZenML `gcp` integration
that uses [GCP](https://cloud.google.com/secret-manager) to store secrets.

{% hint style="warning" %}
We are deprecating secrets managers in favor of
the [centralized ZenML secrets store](/docs/book/platform-guide/set-up-your-mlops-platform/use-the-secret-store/use-the-secret-store.md)
. Going forward, we recommend using the secrets store instead of secrets managers to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your secrets to the centralized secrets store.

To replace GCP Secrets Manager as the service of choice for managing your secrets in the
cloud, [configure your ZenML server to connect to and use the GCP Secrets Manager service](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md)
directly as a back-end for the centralized secrets store and then use `zenml secret` CLI commands to manage your secrets
instead of `zenml secrets-manager secret` CLI commands. You no longer need to register the GCP secrets manager stack
component or add it to your active stack.

Alternatively, you may use any of the other secrets store back-ends that the ZenML server supports, such as AWS Secret
Manager, Azure Key Vault, HashiCorp Vault, or even the ZenML SQL database.
{% endhint %}

### When to use it

You should use the GCP secrets manager if:

* a component of your stack requires a secret for authentication, or you want to use secrets inside your steps.
* you're already using GCP, especially if your orchestrator is running in GCP. If you're using a different cloud
  provider, take a look at the other [secrets manager flavors](secrets-managers.md#secrets-manager-flavors).

### How to deploy it

In order to use the GCP secrets manager, you need to enable
it [here](https://console.cloud.google.com/marketplace/product/google/secretmanager.googleapis.com).

### How to use it

To use the GCP secrets manager, we need:

* The ZenML `gcp` integration installed. If you haven't done so, run

  ```shell
  zenml integration install gcp
  ```
* The [GCP CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.
* The ID of the project in which you want to store secrets.
  Follow [this guide](https://support.google.com/googleapi/answer/7014113?hl=en) to find your project ID.

We can then register the secrets manager and use it in our active stack:

```shell
zenml secrets-manager register <NAME> \
    --flavor=gcp \
    --project_id=<PROJECT_ID>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](secrets-managers.md#in-the-cli) using the CLI
or [fetch secret values inside your steps](secrets-managers.md#in-a-zenml-step).

You can use [secret scoping](secrets-managers.md#secret-scopes) with the GCP Secrets Manager to emulate multiple Secrets
Manager namespaces on top of a single GCP project.

A concrete example of using the GCP secrets manager can be
found [here](https://github.com/zenml-io/zenml/tree/main/examples/cloud\_secrets\_manager).

For more information and a full list of configurable attributes of the GCP secrets manager, check out
the [API Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-gcp/#zenml.integrations.gcp.secrets\_manager.gcp\_secrets\_manager.GCPSecretsManager)
.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
