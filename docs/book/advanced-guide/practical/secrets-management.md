---
description: How to reference secrets when configuring stack components
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


Some of the components in your stack require you to configure them with 
sensitive information like passwords or tokens so they can connect to the 
underlying infrastructure. Secret references allow you to configure these components in
a secure way by not specifying the value directly but instead referencing a secret.
To reference a secret in any string attribute of your stack components, simply specify
the attribute value using the following syntax:

```shell
{{<SECRET_NAME>.<SECRET_KEY>}}
```

For example:

```shell
zenml annotator register label_studio_annotator \
    --flavor=label_studio \
    --authentication_secret={{label_studio_secret.YOUR_AUTH_SECRET_VALUE_GOES_HERE}}
    ...
```

## Register missing secrets for your stack

When using components with secret references in your stack, you need to make sure
that the stack contains a [secrets manager](../../mlops-stacks/secrets-managers/secrets-managers.md)
and all the referenced secrets exist in this secrets manager. To make this process easier, you can
use the following CLI command to interactively register all secrets for a stack:

```shell
zenml stack register-secrets [<STACK_NAME>]
```

## How to use it

### In the CLI

A full guide on using the CLI interface to register, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/#zenml.cli--using-secrets).

{% hint style="info" %}

A ZenML secret is a grouping of key-value pairs which are defined by a schema.
An AWS SecretSchema, for example, has key-value pairs for `AWS_ACCESS_KEY_ID` 
and `AWS_SECRET_ACCESS_KEY` as well as an optional `AWS_SESSION_TOKEN`. If you 
don't specify a schema when registering a secret, ZenML will use the 
`ArbitrarySecretSchema`, a schema where arbitrary keys are allowed.
{% endhint %}

Note that there are two ways you can register or update your secrets. If you
wish to do so interactively, passing the secret name in as an argument
(as in the following example) will initiate an interactive process:

```shell
zenml secrets-manager secret register SECRET_NAME -i
```

If you wish to specify key-value pairs using command line arguments, you can do
so instead:

```shell
zenml secrets-manager secret register SECRET_NAME --key1=value1 --key2=value2
```

For secret values that are too big to pass as a command line argument, or have
special characters, you can also use the special `@` syntax to indicate to ZenML
that the value needs to be read from a file:

```bash
zenml secrets-manager secret register SECRET_NAME --attr_from_literal=value \
   --attr_from_file=@path/to/file.txt ...
```

### In a ZenML Step

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
    """Load the example secret from the secret manager."""
    # Load Secret from active secret manager. This will fail if no secret
    # manager is active or if that secret does not exist.
    retrieved_secret = context.stack.secrets_manager.get_secret(<SECRET_NAME>)

    # retrieved_secret.content will contain a dictionary with all Key-Value
    # pairs within your secret.
    return
```

{% hint style="info" %}
This will only work if the environment that your orchestrator uses to execute 
steps has access to the secrets manager. For example a local secrets manager
will not work in combination with a remote orchestrator.
{% endhint %}


{% hint style="info" %}
To read a more detailed guide about how Secret Managers function in ZenML,
[click here](../../component-gallery/secrets-managers/).
{% endhint %}

## Secret validation

Before running a pipeline, ZenML will validate your stack and make sure that all secrets
and keys referenced in your stack components exist. This helps us fail early so your 
pipeline doesn't fail after running for some time due to some missing secret.

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