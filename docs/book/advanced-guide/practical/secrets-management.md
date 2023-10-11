---
description: How to register and use secrets
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## What is a ZenML secret

ZenML secrets are groupings of **key-value pairs** which are securely stored by
your ZenML [secrets manager](../../component-gallery/secrets-managers/secrets-managers.md).
Additionally, a secret always has a **name** which allows you to fetch or reference
them in your pipelines and stacks.

## How to register a secret

{% hint style="info" %}
To register a secret, you'll need a [secrets manager](../../component-gallery/secrets-managers/secrets-managers.md)
in your active stack.
{% endhint %}

To register a secret with name `<SECRET_NAME>` and a key-value pair, you
can then run the following CLI command:
```shell
zenml secrets-manager secret register <SECRET_NAME> \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>
```

Alternatively, you can start an interactive registration (in which ZenML will query you for
the secret keys and values) by passing the
`--interactive/-i` parameter:

```shell
zenml secrets-manager secret register <SECRET_NAME> -i
```

For secret values that are too big to pass as a command line argument, or have
special characters, you can also use the special `@` syntax to indicate to ZenML
that the value needs to be read from a file:

```bash
zenml secrets-manager secret register <SECRET_NAME> \
   --key=@path/to/file.txt \
   ...
```

A full guide on using the CLI to register, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/#zenml.cli--using-secrets).

### Interactively register missing secrets for your stack

If you're using components with
[secret references](#reference-secrets-in-stack-component-attributes-and-settings)
in your stack, you need to make sure that the stack contains a
[secrets manager](../../component-gallery/secrets-managers/secrets-managers.md)
and all the referenced secrets exist in this secrets manager. To make this process easier, you can
use the following CLI command to interactively register all secrets for a stack:

```shell
zenml stack register-secrets [<STACK_NAME>]
```

## How to use registered secrets

### Reference secrets in stack component attributes and settings

Some of the components in your stack require you to configure them with 
sensitive information like passwords or tokens so they can connect to the 
underlying infrastructure. Secret references allow you to configure these components in
a secure way by not specifying the value directly but instead referencing a secret by providing
the secret name and key.
Referencing a secret for the value of any string attribute of your stack components, simply specify
the attribute using the following syntax: `{{<SECRET_NAME>.<SECRET_KEY>}}`

For example:
```shell
# Register a secret called `mlflow_secret` with key-value pairs for the
# username and password to authenticate with the MLflow tracking server
zenml secrets-manager secret register mlflow_secret \
    --username=admin \
    --password=abc123

# Reference the username and password in our experiment tracker component
zenml experiment-tracker register mlflow \
    --flavor=mlflow \
    --tracking_username={{mlflow_secret.username}} \
    --tracking_password={{mlflow_secret.password}} \
    ...
```

When using secret references in your stack, ZenML will validate that all secrets
and keys referenced in your stack components exist before running a pipeline.
This helps us fail early so your pipeline doesn't fail after running for some
time due to some missing secret.

This validation by default needs to fetch and read every secret to make sure that
both the secret and the specified key-value pair exist. This can take quite some time and
might fail if you don't have the permissions to read secrets.

You can use the environment variable `ZENML_SECRET_VALIDATION_LEVEL` to disable or 
control the degree to which ZenML validates your secrets:

* Setting it to `NONE` disables any validation.
* Setting it to `SECRET_EXISTS` only validates the existence of secrets. This might be useful
if the machine you're running on only has permissions to list secrets but not actually read
their values.
* Setting it to `SECRET_AND_KEY_EXISTS` (the default) validates both the secret existence as
well as the existence of the exact key-value pair.

### Fetch secret values in a step

You can access the secrets manager directly from within your steps through the 
`StepContext`. This allows you to use your secrets for querying APIs from 
within your step without hard-coding your access keys. Don't forget to 
make the appropriate decision regarding caching as it will be disabled by 
default when the `StepContext` is passed into the step.

```python
from zenml.steps import step, StepContext


@step(enable_cache=True)
def secret_loader(
    context: StepContext,
) -> None:
    """Load the example secret from the secrets manager."""
    # Load Secret from active secrets manager. This will fail if no secret
    # manager is active or if that secret does not exist.
    retrieved_secret = context.stack.secrets_manager.get_secret(<SECRET_NAME>)

    # retrieved_secret.content will contain a dictionary with all key-value
    # pairs within your secret.
    return
```

{% hint style="info" %}
This will only work if the environment that your orchestrator uses to execute 
steps has access to the secrets manager. For example a local secrets manager
will not work in combination with a remote orchestrator.
{% endhint %}
