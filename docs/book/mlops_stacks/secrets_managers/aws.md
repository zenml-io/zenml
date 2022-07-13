---
description: Store secrets in AWS
---

The AWS secrets manager is a [secrets manager](./overview.md) flavor provided with
the ZenML `aws` integration that uses [AWS](https://aws.amazon.com/secrets-manager/)
to store secrets.

## When to use it

You should use the AWS secrets manager if:
* a component of your stack requires a secret for authentication or you want 
to use secrets inside your steps.
* you're already using AWS, especially if your orchestrator is running in AWS.
If you're using a different cloud provider, take a look at the other [secrets manager flavors](./overview.md#secrets-manager-flavors).
## How to deploy it

The AWS secrets manager is automatically activated once you create an AWS account.

## How to use it

To use the AWS secrets manager, we need:
* The ZenML `aws` integration installed. If you haven't done so, run 
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

You can now [register, update or delete secrets](./overview.md#in-the-cli) using the CLI or [fetch secret values inside your steps](./overview.md#in-a-zenml-step).

A concrete example of using the AWS secrets manager can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/cloud_secrets_manager).

For more information and a full list of configurable attributes of the AWS secrets manager, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.aws.secrets_managers.aws_secrets_manager.AWSSecretsManager).
