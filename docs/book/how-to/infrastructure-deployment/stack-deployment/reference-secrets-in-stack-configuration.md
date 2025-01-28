---
description: Reference secrets in stack component attributes and settings
---

# Reference secrets in stack configuration

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

If you are using [centralized secrets management](../../interact-with-secrets.md), you can access secrets directly from within your steps through the ZenML `Client` API. This allows you to use your secrets for querying APIs from within your step without hard-coding your access keys:

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

## See Also

- [Interact with secrets](../../interact-with-secrets.md): Learn how to create,
  list, and delete secrets using the ZenML CLI and Python SDK.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
