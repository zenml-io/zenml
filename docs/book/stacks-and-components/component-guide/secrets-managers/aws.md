---
description: Storing secrets in AWS
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# AWS Secrets Manager

The AWS secrets manager is a [secrets manager](./) flavor provided with the ZenML `aws` integration that uses [AWS](https://aws.amazon.com/secrets-manager/) to store secrets.

{% hint style="warning" %}
We are deprecating secrets managers in favor of the [centralized ZenML secrets store](../../../user-guide/advanced-guide/secret-management/) . Going forward, we recommend using the secrets store instead of secrets managers to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the provided `zenml secrets-manager secrets migrate` CLI command to migrate your secrets to the centralized secrets store.

To continue using AWS Secrets Manager as the service of choice for managing your secrets in the cloud, [configure your ZenML server to connect to and use the AWS Secrets Manager service](../../../deploying-zenml/zenml-self-hosted/) directly as a back-end for the centralized secrets store and then use `zenml secret` CLI commands to manage your secrets instead of `zenml secrets-manager secret` CLI commands. You no longer need to register the AWS secrets manager stack component or add it to your active stack.

Alternatively, you may use any of the other secrets store back-ends that the ZenML server supports, such as Google Secret Manager, Azure Key Vault, HashiCorp Vault, or even the ZenML SQL database.
{% endhint %}

### When to use it

You should use the AWS secrets manager if:

* a component of your stack requires a secret for authentication, or you want to use secrets inside your steps.
* you're already using AWS, especially if your orchestrator is running in AWS. If you're using a different cloud provider, take a look at the other [secrets manager flavors](./#secrets-manager-flavors).

### How to deploy it

The AWS secrets manager is automatically activated once you create an AWS account.

### How to use it

To use the AWS secrets manager, we need:

*   The ZenML `aws` integration installed. If you haven't done so, run

    ```shell
    zenml integration install aws
    ```
* The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and authenticated.
* A region in which you want to store your secrets. Choose one from the list [here](https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints).

We can then register the secrets manager and use it in our active stack:

```shell
zenml secrets-manager register <NAME> \
    --flavor=aws \
    --region_name=<REGION>

# Add the secrets manager to the active stack
zenml stack update -x <NAME>
```

You can now [register, update or delete secrets](./#in-the-cli) using the CLI or [fetch secret values inside your steps](./#in-a-zenml-step).

You can use [secret scoping](./#secret-scopes) with the AWS Secrets Manager to emulate multiple Secrets Manager namespaces on top of a single AWS region.

For more information and a full list of configurable attributes of the AWS secrets manager, check out the [API Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-aws/#zenml.integrations.aws.secrets\_managers.aws\_secrets\_manager.AWSSecretsManager) .

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
