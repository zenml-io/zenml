---
description: Setting up storage for secrets
---

Secrets managers provide a secure way of storing confidential information
that is needed to run your ML pipelines. Most production pipelines will run
on cloud infrastructure and therefore need credentials to authenticate with 
those services. Instead of storing these credentials in code or files, 
ZenML secrets managers can be used to store and retrieve these values
in a secure manner.

## When to use it

You should include a secrets manager in your ZenML stack if any other component
of your stack requires confidential information (such as authentication credentials)
or you want to access secret values inside your pipeline steps.

## Secrets Manager Flavors

Out of the box, ZenML comes with a `local` secrets manager that stores secrets in local 
files. Additional cloud secrets managers are provided by integrations:

| Secrets Manager | Flavor | Integration | Notes             |
|----------------|--------|-------------|-------------------|
| [Local](./local.md) | `local` | _built-in_ | Uses local files to store secrets |
| [AWS](./aws.md) | `aws` | `aws` |  Uses AWS to store secrets |
| [GCP](./gcp.md) | `gcp_secrets_manager` | `gcp` |  Uses GCP to store secretes |
| [Azure](./azure.md) | `azure_key_vault` | `azure` |  Uses Azure Key Vaults to store secrets |
| [HashiCorp Vault](./hashicorp_vault.md) | `vault` | `vault` |  Uses HashiCorp Vault to store secrets |
| [Custom Implementation](./custom.md) | _custom_ | | Extend the secrets manager abstraction and provide your own implementation |

If you would like to see the available flavors of secrets managers, you can 
use the command:

```shell
zenml secrets-manager flavor list
```
## How to use it

### In the CLI

A full guide on using the CLI interface to register, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/).

{% hint style="info" %}

A ZenML secret is a grouping of key-value pairs which are defined by a schema.
An AWS SecretSchema, for example, has key-value pairs for `AWS_ACCESS_KEY_ID` and
 `AWS_SECRET_ACCESS_KEY` as well as an optional `AWS_SESSION_TOKEN`. If you don't
specify a schema when registering a secret, ZenML will use the `ArbitrarySecretSchema`,
a schema where arbitrary keys are allowed.

{% endhint %}

Note that there are two ways you can register or update your secrets. If you
wish to do so interactively, passing the secret name in as an argument
(as in the following example) will initiate an interactive process:

```shell
zenml secret register SECRET_NAME -i
```

If you wish to specify key-value pairs using command line arguments, you can do
so instead:

```shell
zenml secret register SECRET_NAME --key1=value1 --key2=value2
```

For secret values that are too big to pass as a command line argument, or have
special characters, you can also use the special `@` syntax to indicate to ZenML
that the value needs to be read from a file:

```bash
zenml secret register SECRET_NAME --attr_from_literal=value \
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

This will only work if the environment that your ochestrator uses to execute steps 
has access to the secrets manager. For example a local secrets manager
will not work in combination with a remote orchestrator.

{% endhint %}

## Secret Schemas

The concept of secret schemas exists to support strongly typed secrets that
validate which keys can be configured for a given secret and which values are
allowed for those keys.

Secret schemas are available as builtin schemas, or loaded when an integration
is installed. Custom schemas can also be defined by sub-classing the
`zenml.secret.BaseSecretSchema` class. For example, the following is the builtin
schema defined for the MySQL Metadata Store secrets:

```python
from typing import ClassVar, Optional

from zenml.secret.base_secret import BaseSecretSchema

MYSQL_METADATA_STORE_SCHEMA_TYPE = "mysql"

class MYSQLSecretSchema(BaseSecretSchema):
    TYPE: ClassVar[str] = MYSQL_METADATA_STORE_SCHEMA_TYPE

    user: Optional[str]
    password: Optional[str]
    ssl_ca: Optional[str]
    ssl_cert: Optional[str]
    ssl_key: Optional[str]
    ssl_verify_server_cert: Optional[bool] = False
```

To register a secret regulated by a schema, the `--schema` argument must be
passed to the `zenml secret register` command:

```shell
zenml secret register mysql_secret --schema=mysql --user=user --password=password
--ssl_ca=@./ca.pem --ssl_verify_server_cert=true
```

The keys and values passed to the CLI are validated using regular Pydantic
rules:

* optional attributes don't need to be passed to the CLI and will be set to
their default value if omitted
* required attributes must be passed to the CLI or an error will be raised
* all values must be a valid string representation of the data type indicated in
the schema (i.e. that can be converted to the type indicated) or an error will
be raised
