---
icon: user-secret
description: Registering and using secrets.
icon: user-secret
---

# Interact with secrets

## What is a ZenML secret?

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks.

## How to create a secret

{% tabs %}
{% tab title="CLI" %}
To create a secret with a name `<SECRET_NAME>` and a key-value pair, you can run the following CLI command:

```shell
zenml secret create <SECRET_NAME> \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>

# Another option is to use the '--values' option and provide key-value pairs in either JSON or YAML format.
zenml secret create <SECRET_NAME> \
    --values='{"key1":"value2","key2":"value2"}'
```

Alternatively, you can create the secret in an interactive session (in which ZenML will query you for the secret keys and values) by passing the `--interactive/-i` parameter:

```shell
zenml secret create <SECRET_NAME> -i
```

For secret values that are too big to pass as a command line argument, or have special characters, you can also use the special `@` syntax to indicate to ZenML that the value needs to be read from a file:

```bash
zenml secret create <SECRET_NAME> \
   --key=@path/to/file.txt \
   ...
   
# Alternatively, you can utilize the '--values' option by specifying a file path containing key-value pairs in either JSON or YAML format.
zenml secret create <SECRET_NAME> \
    --values=@path/to/file.txt
```

The CLI also includes commands that can be used to list, update and delete secrets. A full guide on using the CLI to create, access, update and delete secrets is available [here](https://sdkdocs.zenml.io/latest/cli/#zenml.cli--secrets-management).

**Interactively register missing secrets for your stack**

If you're using components with [secret references](interact-with-secrets.md#reference-secrets-in-stack-component-attributes-and-settings) in your stack, you need to make sure that all the referenced secrets exist. To make this process easier, you can use the following CLI command to interactively register all secrets for a stack:

```shell
zenml stack register-secrets [<STACK_NAME>]
```
{% endtab %}

{% tab title="Python SDK" %}
The ZenML client API offers a programmatic interface to create, e.g.:

```python
from zenml.client import Client

client = Client()
client.create_secret(
    name="my_secret",
    values={
        "username": "admin",
        "password": "abc123"
    }
)
```

Other Client methods used for secrets management include `get_secret` to fetch a secret by name or id, `update_secret` to update an existing secret, `list_secrets` to query the secrets store using a variety of filtering and sorting criteria, and `delete_secret` to delete a secret. The full Client API reference is available [here](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-client/).
{% endtab %}
{% endtabs %}

## Set scope for secrets

ZenML secrets can be scoped to a user. This allows you to create secrets that are only accessible to one user.

By default, all created secrets are scoped to the active user. To create a secret and scope it to your active user instead, you can pass the `--scope` argument to the CLI command:

```shell
zenml secret create <SECRET_NAME> \
    --scope user \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>
```

Scopes also act as individual namespaces. When you are referencing a secret by name in your pipelines and stacks, ZenML will look for a secret with that name scoped to the active user.

## Accessing registered secrets

### Reference secrets in stack component attributes and settings

Some of the components in your stack require you to configure them with sensitive information like passwords or tokens, so they can connect to the underlying infrastructure. Secret references allow you to configure these components in a secure way by not specifying the value directly but instead referencing a secret by providing the secret name and key. Referencing a secret for the value of any string attribute of your stack components, simply specify the attribute using the following syntax: `{{<SECRET_NAME>.<SECRET_KEY>}}`

For example:

{% tabs %}
{% tab title="CLI" %}
```shell
# Register a secret called `mlflow_secret` with key-value pairs for the
# username and password to authenticate with the MLflow tracking server

# Using central secrets management
zenml secret create mlflow_secret \
    --username=admin \
    --password=abc123
    

# Then reference the username and password in our experiment tracker component
zenml experiment-tracker register mlflow \
    --flavor=mlflow \
    --tracking_username={{mlflow_secret.username}} \
    --tracking_password={{mlflow_secret.password}} \
    ...
```
{% endtab %}
{% endtabs %}

When using secret references in your stack, ZenML will validate that all secrets and keys referenced in your stack components exist before running a pipeline. This helps us fail early so your pipeline doesn't fail after running for some time due to some missing secret.

This validation by default needs to fetch and read every secret to make sure that both the secret and the specified key-value pair exist. This can take quite some time and might fail if you don't have permission to read secrets.

You can use the environment variable `ZENML_SECRET_VALIDATION_LEVEL` to disable or control the degree to which ZenML validates your secrets:

* Setting it to `NONE` disables any validation.
* Setting it to `SECRET_EXISTS` only validates the existence of secrets. This might be useful if the machine you're running on only has permission to list secrets but not actually read their values.
* Setting it to `SECRET_AND_KEY_EXISTS` (the default) validates both the secret existence as well as the existence of the exact key-value pair.

### Fetch secret values in a step

If you are using [centralized secrets management](interact-with-secrets.md), you can access secrets directly from within your steps through the ZenML `Client` API. This allows you to use your secrets for querying APIs from within your step without hard-coding your access keys:

```python
from zenml import step
from zenml.client import Client


@step
def secret_loader() -> None:
    """Load the example secret from the server."""
    # Fetch the secret from ZenML.
    secret = Client().get_secret( < SECRET_NAME >)

    # `secret.secret_values` will contain a dictionary with all key-value
    # pairs within your secret.
    authenticate_to_some_api(
        username=secret.secret_values["username"],
        password=secret.secret_values["password"],
    )
    ...
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
