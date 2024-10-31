# Access secrets in a step

## Fetching secret values in a step

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a
secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks. In order to learn
more about how to configure and create secrets, please refer to
the [platform guide on secrets](../../getting-started/deploying-zenml/secret-management.md).

You can access secrets directly from within your steps through the ZenML `Client` API. This allows you to use your
secrets for querying APIs from within your step without hard-coding your access keys:

```python
from zenml import step
from zenml.client import Client

from somewhere import authenticate_to_some_api


@step
def secret_loader() -> None:
    """Load the example secret from the server."""
    # Fetch the secret from ZenML.
    secret = Client().get_secret("<SECRET_NAME>")

    # `secret.secret_values` will contain a dictionary with all key-value
    # pairs within your secret.
    authenticate_to_some_api(
        username=secret.secret_values["username"],
        password=secret.secret_values["password"],
    )
    ...
```


***

### See Also:


<table data-view="cards">
    <thead>
    <tr>
        <th></th>
        <th></th>
        <th></th>
        <th data-hidden data-card-target data-type="content-ref"></th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td>Learn how to create and manage secrets</td>
        <td></td>
        <td></td>
        <td><a href="../interact-with-secrets.md">interact-with-secrets.md</a></td>
    </tr>
    <tr>
        <td>Find out more about the secrets backend in ZenML</td>
        <td></td>
        <td></td>
        <td><a href="../../getting-started/deploying-zenml/secret-management.md">secret-management.md</a></td>
    </tr>
    </tbody>
</table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


