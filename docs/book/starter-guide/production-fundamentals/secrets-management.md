---
description: How to register and use secrets
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## What is a ZenML secret

ZenML secrets are groupings of **key-value pairs** which are securely stored in
the ZenML secrets store. Additionally, a secret always has a **name** which
allows you to fetch or reference them in your pipelines and stacks.

{% hint style="warning" %}
We are deprecating Secrets Managers in favor of [the centralized ZenML secrets store](#centralized-secrets-store).
Going forward, we recommend using the ZenML secrets store instead of secrets
manager stack components to configure and store secrets. [Referencing secrets in your pipelines and stacks](#how-to-use-registered-secrets)
works the same way regardless of whether you are using a secrets manager or the
centralized secrets store.
If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your
secrets to the centralized secrets store.
{% endhint %}

## Centralized secrets store

ZenML provides a centralized secrets management system that allows you to
register and manage secrets in a secure way. When you are using a local ZenML
deployment, the secrets are stored in the local SQLite database. If you are
connected to a remote ZenML server, the secrets are stored in the secrets
management back-end that the server is configured to use, but all access to the
secrets is done through the ZenML server API.

Currently, the ZenML server can be configured to use one of the following
supported secrets store back-ends:

* the SQL database that the ZenML server is using to store other managed objects
such as pipelines, stacks, etc. This is the default option.
* the AWS Secrets Manager
* the GCP Secret Manager
* the Azure Key Vault
* the HashiCorp Vault
* a custom secrets store back-end implementation is also supported

Configuring the specific secrets store back-end that the ZenML server uses is
done at deployment time. For more information on how to deploy a ZenML server
and configure the secrets store back-end, refer to the [deployment guide](../../getting-started/deploying-zenml/deploying-zenml.md).

### How to create a secret with the CLI

To create a secret with name `<SECRET_NAME>` and a key-value pair, you
can run the following CLI command:
```shell
zenml secret create <SECRET_NAME> \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>
```

Alternatively, you can start an interactive creation (in which ZenML will query you for
the secret keys and values) by passing the
`--interactive/-i` parameter:

```shell
zenml secret create <SECRET_NAME> -i
```

For secret values that are too big to pass as a command line argument, or have
special characters, you can also use the special `@` syntax to indicate to ZenML
that the value needs to be read from a file:

```bash
zenml secret create <SECRET_NAME> \
   --key=@path/to/file.txt \
   ...
```

The CLI also includes commands that can be used to list, update and delete
secrets. A full guide on using the CLI to create, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/#zenml.cli--secrets-management).

### How to create a secret with the ZenML Client API

The ZenML client API offers a programmatic interface to create, e.g.:

```python
from zenml.client import Client

client = Client()
client.create_secret(
    name = "my_secret",
    values = {
        "username": "admin",
        "password": "abc123"
    }
)
```

Other Client methods used for secrets management include `get_secret` to fetch
a secret by name or id, `update_secret` to update an existing secret,
`list_secrets` to query the secrets store using a variety of filtering and
sorting criteria and `delete_secret` to delete a secret. The full Client API
reference is available [here](https://apidocs.zenml.io/latest/core_code_docs/core-client/).

### Secrets scoping

ZenML secrets can be scoped to a workspace or a user. This allows you to
create secrets that are only accessible to a specific workspace or user.

By default, all created secrets are scoped to the active workspace. To
create a secret and scope it to your active user instead, you can pass the
`--scope` argument to the CLI command:

```shell
zenml secret create <SECRET_NAME> \
    --scope user \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>
```

Scopes also act as individual namespaces. When you are referencing a secret by
name in your pipelines and stacks, ZenML will first look for a secret with
that name scoped to the active user, and if it doesn't find one, it will look
for one in the active workspace.

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

# Using central secrets management
zenml secret create mlflow_secret \
    --username=admin \
    --password=abc123

# Or using a secrets manager
zenml secrets-manager secret register mlflow_secret \
    --username=admin \
    --password=abc123

# Then reference the username and password in our experiment tracker component
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


{% hint style="warning" %}
If you have secrets registered through both the [centralized secrets management](#centralized-secrets-store)
and [a secrets manager](#secrets-management-with-secrets-managers), ZenML will
first try to fetch the secret from the centralized secrets management and only
fall back to the secrets manager if the secret is not found. This means that if
you have a secret registered with the same name in both the centralized secrets
store and the secrets manager, the secret registered in the secrets store
will take precedence.
{% endhint %}

### Fetch secret values in a step

If you are using [centralized secrets management](#centralized-secrets-store),
you can access secrets directly from within your steps through the 
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

If you are using a Secrets Manager to manage secrets, you can access the secrets
manager directly from within your steps through the `StepContext`. This allows
you to use your secrets for querying APIs from  within your step without
hard-coding your access keys. Don't forget to make the appropriate decision
regarding caching as it will be disabled by default when the `StepContext` is
passed into the step.

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


## Secrets management with Secrets Managers

[Secrets Managers](../../component-gallery/secrets-managers/secrets-managers.md)
are ZenML stack components that allow you to register and access secrets when
used as part of your active stack.

{% hint style="warning" %}
We are deprecating secrets managers in favor of the [centralized ZenML secrets store](#centralized-secrets-store).
Going forward, we recommend using the secrets store instead of secrets managers
to configure and store secrets.

If you already use secrets managers to manage your secrets, please use the
provided `zenml secrets-manager secrets migrate` CLI command to migrate your
secrets to the centralized secrets store.

Managing secrets through a secrets manager stack component suffers from a
number of limitations, some of which are:

* you need to configure [a Secrets Manager stack component](../../component-gallery/secrets-managers/secrets-managers.md)
and add it to your active stack before you can register and access secrets. With
centralized secrets management, you don't need to configure anything, your ZenML
local deployment or ZenML server takes on the secrets manager role.

* even with a secrets manager configured in your active stack, if you are using
a secrets manager flavor with a cloud back-end (e.g. AWS, GCP or Azure), you
still need to configure all your ZenML clients with the authentication credentials
required to access the back-end directly. This is not only an inconvenience, it
is also a security risk, because it basically represents a large attack surface.
With centralized secrets management, you only need to configure the ZenML server
to access the cloud back-end.

{% endhint %}

### How to register a secret

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
secrets is available [here](https://apidocs.zenml.io/latest/cli/#zenml.cli--secrets-management-with-secrets-managers).

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


## Implement your own secrets store backend

The secrets store acts as the one-stop shop for all the secrets to which your 
pipeline or stack components might need access. The secrets store interface
implemented by all available secrets store back-ends is defined in the
`zenml.zen_stores.secrets_stores.secrets_store_interface` core module and looks
more or less like this:

```python
class SecretsStoreInterface(ABC):
    """ZenML secrets store interface.

    All ZenML secrets stores must implement the methods in this interface.
    """

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the secrets store.
        """

    @abstractmethod
    def create_secret(
        self,
        secret: SecretRequestModel,
    ) -> SecretResponseModel:
        """Creates a new secret.
        """

    @abstractmethod
    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret with a given name.
        """

    @abstractmethod
    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.
        """

    @abstractmethod
    def update_secret(
        self,
        secret_id: UUID,
        secret_update: SecretUpdateModel,
    ) -> SecretResponseModel:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).
        """

    @abstractmethod
    def delete_secret(self, secret_id: UUID) -> None:
        """Deletes a secret.
        """

```

{% hint style="info" %}
This is a slimmed-down version of the real interface which aims to 
highlight the abstraction layer. In order to see the full definition 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/latest/core_code_docs/core-zen_stores/#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface).
{% endhint %}

### Build your own custom secrets manager

If you want to create your own custom secrets store implementation, you can 
follow the following steps:

1. Create a class which inherits from the `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsManager` base class and implement the `abstractmethod`s shown in the interface above.
Use `SecretsStoreType.CUSTOM` as the `TYPE` value for your secrets store class.
2. If you need to provide any configuration, create a class which inherits 
from the `SecretsStoreConfiguration` class and add your configuration
parameters there. Use that as the `CONFIG_TYPE` value for your secrets store
class.
3. To configure the ZenML server to use your custom secrets store, make sure
your code is available in the container image that is used to run the ZenML
server. Then, use environment variables or helm chart values to configure the
ZenML server to use your custom secrets store, as covered in the
[deployment guide](../../getting-started/deploying-zenml/deploying-zenml.md).
