---
description: Registering and using secrets.
icon: user-secret
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Secrets

ZenML secrets are groupings of **key-value pairs** which are securely stored in the ZenML secrets store. Additionally, a secret always has a **name** that allows you to fetch or reference them in your pipelines and stacks. Secrets are essential for both traditional ML workflows (database credentials, model registry access) and AI agent development (LLM API keys, third-party service credentials).

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

# Example: Create secrets for LLM API keys
zenml secret create openai_secret \
    --api_key=sk-proj-... \
    --organization_id=org-...

zenml secret create anthropic_secret \
    --api_key=sk-ant-api03-...

# Example: Create secrets for multi-agent system credentials
zenml secret create agent_tools_secret \
    --google_search_api_key=AIza... \
    --weather_api_key=abc123 \
    --database_url=postgresql://user:pass@host/db

# Create a private secret (only you can access it)
zenml secret create my_private_secret --private \
    --api_key=secret-value
```

{% hint style="info" %}
By default, secrets are public (visible to other users based on RBAC). Use `--private` or `-p` to create a secret only you can access. See [Private and public secrets](#private-and-public-secrets) for more details.
{% endhint %}

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

The CLI also includes commands that can be used to list, update and delete secrets. A full guide on using the CLI to create, access, update and delete secrets is available [here](https://sdkdocs.zenml.io/latest/cli.html#zenml.cli--secrets-management).

**Interactively register missing secrets for your stack**

If you're using components with [secret references](secrets.md#reference-secrets-in-stack-component-attributes-and-settings) in your stack, you need to make sure that all the referenced secrets exist. To make this process easier, you can use the following CLI command to interactively register all secrets for a stack:

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

# Example: Create LLM API secrets programmatically
client.create_secret(
    name="openai_secret",
    values={
        "api_key": "sk-proj-...",
        "organization_id": "org-..."
    }
)

# Create a private secret (only you can access it)
client.create_secret(
    name="my_private_secret",
    values={"api_key": "secret-value"},
    private=True,
)
```

{% hint style="info" %}
By default, secrets are public (`private=False`). Set `private=True` to create a secret only you can access. See [Private and public secrets](#private-and-public-secrets) for more details.
{% endhint %}

Other Client methods used for secrets management include `get_secret` to fetch a secret by name or id, `update_secret` to update an existing secret, `list_secrets` to query the secrets store using a variety of filtering and sorting criteria, and `delete_secret` to delete a secret. The full Client API reference is available [here](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html).
{% endtab %}
{% endtabs %}

## Private and public secrets

ZenML secrets can be either **private** or **public**:

- **Private secrets** are only accessible to the user who created them. No other user can view, use, or manage a private secret, regardless of their role or permissions.
- **Public secrets** (the default) are accessible to other users based on your RBAC configuration. On ZenML Pro, access to public secrets is governed by your role-based access control settings.

{% hint style="info" %}
The `private` property takes precedence over RBAC. A private secret is **only** visible to its creator, even if RBAC would otherwise grant access to other users.
{% endhint %}

### Creating private secrets

By default, secrets are created as public (`private=False`). To create a private secret:

{% tabs %}
{% tab title="CLI" %}
```shell
# Use the --private or -p flag
zenml secret create <SECRET_NAME> --private \
    --<KEY_1>=<VALUE_1> \
    --<KEY_2>=<VALUE_2>

# Short form
zenml secret create <SECRET_NAME> -p \
    --<KEY_1>=<VALUE_1>
```
{% endtab %}

{% tab title="Python SDK" %}
```python
from zenml.client import Client

client = Client()
client.create_secret(
    name="my_private_secret",
    values={"api_key": "..."},
    private=True,  # Makes this secret private
)
```
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
Currently, setting the private status is only available via the CLI and Python SDK. The dashboard UI does not yet support creating or modifying private secrets.
{% endhint %}

### Fetching secrets with the same name

Since private and public secrets exist in separate namespaces, you can have both a private and a public secret with the same name. When fetching a secret by name without specifying its visibility:

- ZenML searches **private secrets first**, then public secrets
- The first match is returned

To explicitly fetch a secret of a specific visibility:

{% tabs %}
{% tab title="CLI" %}
```shell
# Explicitly fetch a private secret
zenml secret get my_secret --private=true

# Explicitly fetch a public secret
zenml secret get my_secret --private=false
```
{% endtab %}

{% tab title="Python SDK" %}
```python
from zenml.client import Client

client = Client()

# Explicitly fetch a private secret
private_secret = client.get_secret("my_secret", private=True)

# Explicitly fetch a public secret
public_secret = client.get_secret("my_secret", private=False)
```
{% endtab %}
{% endtabs %}

### Updating secret visibility

You can change a secret's visibility after creation:

{% tabs %}
{% tab title="CLI" %}
```shell
# Make a public secret private
zenml secret update my_secret --private=true

# Make a private secret public
zenml secret update my_secret --private=false
```
{% endtab %}

{% tab title="Python SDK" %}
```python
from zenml.client import Client

client = Client()
client.update_secret("my_secret", update_private=True)  # Make private
```
{% endtab %}
{% endtabs %}

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

If you are using [centralized secrets management](secrets.md), you can access secrets directly from within your steps through the ZenML `Client` API. This allows you to use your secrets for querying APIs from within your step without hard-coding your access keys:

```python
from zenml import step
from zenml.client import Client
import openai

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

@step
def run_llm_agent(prompt: str, query: str) -> str:
    """Execute an LLM agent using securely stored API keys."""
    # Fetch LLM API credentials from ZenML secrets
    openai_secret = Client().get_secret("openai_secret")
    
    # Use the API key to initialize the LLM client
@step
def run_llm_agent(prompt: str, query: str) -> str:
    """Execute an LLM agent using securely stored API keys."""
    # Fetch LLM API credentials from ZenML secrets
    openai_secret = Client().get_secret("openai_secret")
    
    # Initialize the OpenAI client with credentials
    from openai import OpenAI
    
    client = OpenAI(
        api_key=openai_secret.secret_values["api_key"],
        organization=openai_secret.secret_values["organization_id"]
    )
    
    # Execute the agent
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ]
    )
    
    return response.choices[0].message.content
    return response.choices[0].message.content
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
