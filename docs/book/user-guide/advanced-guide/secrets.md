---
description: How to use secrets in your pipeines
---

## What is a ZenML secret

ZenML secrets are groupings of **key-value pairs** which are securely stored in
the ZenML secrets store. Additionally, a secret always has a **name** which
allows you to fetch or reference them in your pipelines and stacks.

To learn more about how to configure and create secrets, please refer to the
[platform guide on secrets](../../platform-guide/set-up-your-mlops-platform/secrets-management.md).
This guide will be focused on using already registered secrets in a pipeline.

## How to fetch secret values in a step

You can access secrets directly from within your steps through the 
ZenML `Client` API. This allows you to use your secrets for querying APIs from 
within your step without hard-coding your access keys:

```python
from zenml.steps import step
from zenml.client import Client

@step
def secret_loader() -> None:
    """Load the example secret from the server."""
    # Fetch the secret from ZenML.
    secret = Client().get_secret(<SECRET_NAME>)

    # `secret.secret_values` will contain a dictionary with all key-value
    # pairs within your secret.
    authenticate_to_some_api(
        username = secret.secret_values["username"],
        password = secret.secret_values["password"],
    )
    ...
```

## Secret values as environment variables

We should talk here about this if it exists...