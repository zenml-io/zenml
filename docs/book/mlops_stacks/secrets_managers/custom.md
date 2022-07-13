---
description: Implement a custom secrets manager
---

{% hint style="warning" %}
Before reading this page, make sure that you are familiar with the
concept of [stacks, stack components and their flavors](../advanced-guide/stacks-components-flavors.md).  
{% endhint %}

## Base Abstraction

The secret manager acts as the one-stop shop for all the secrets to which your 
pipeline or stack components might need access. 

1. As it is the base class for a specific type of `StackComponent`,
    it inherits from the StackComponent class. This sets the `TYPE`
    variable to the secrets manager . The `FLAVOR` class variable needs to be 
    set in the specific subclass.
2. The `BaseSecretsManager` implements the interface for a set of CRUD
    operations as `abstractmethod`s: `register_secret`, `get_secret`, 
    `get_all_secret_keys`, `update_secret`, `delete_secret`, 
    `delete_all_secrets`. In the implementation of every 
   `SecretsManager` flavor, it is required to define these methods with respect 
    to the flavor at hand.

```python
from abc import ABC, abstractmethod
from typing import ClassVar, List

from zenml.enums import StackComponentType
from zenml.secret.base_secret import BaseSecretSchema
from zenml.stack import StackComponent

class BaseSecretsManager(StackComponent, ABC):
    """Base class for all ZenML secrets managers."""

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.SECRETS_MANAGER
    FLAVOR: ClassVar[str]

    @abstractmethod
    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret."""

    @abstractmethod
    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret."""

    @abstractmethod
    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""

    @abstractmethod
    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret."""

    @abstractmethod
    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret."""

    @abstractmethod
    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/0.7.3/api_docs/secrets_managers/#zenml.secrets_managers.base_secrets_manager.BaseSecretsManager).
{% endhint %}

## Build your own custom secrets manager

If you want to create your own custom flavor for a secrets manager, you can 
follow the following steps:

1. Create a class which inherits from the `BaseSecretsManager`.
2. Define the `FLAVOR` class variable.
3. Implement the `abstactmethod`s based on the API of your desired secrets 
manager

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml secrets-manager flavor register <THE-SOURCE-PATH-OF-YOUR-SECRETS-MANAGER>
```

# Some additional implementation details

Different providers in the space of secrets manager have different definitions 
of what constitutes a secret. While some providers consider a single key-value 
pair a secret: (`'secret_name': 'secret_value'`), other providers have a slightly 
different definition. For them, a secret is a collection of key-value pairs:
`{'some_username': 'user_name_1', 'some_pwd': '1234'}`.

ZenML falls into the second category. The implementation of the different 
methods should reflect this convention. In case the specific implementation 
interfaces with a secrets manager that uses the other definition of a secret, 
working with tags can be helpful. See the `GCPSecretsManager` for inspiration.

## SecretSchemas

One way that ZenML expands on the notion of secrets as dictionaries is the 
secret schema. A secret schema allows the user to create and use a specific 
template. A schema could, for example, require the combination of a username,
password and token. All schemas must sub-class from the `BaseSecretSchema`.

1. All Secret Schemas will need to have a defined `TYPE`.
2. The required and optional keys of the secret need to be defined as class
    variables.

```python
class BaseSecretSchema(BaseModel, ABC):
    name: str
    TYPE: ClassVar[str]

    @property
    def content(self) -> Dict[str, Any]:
        ...
```

One such schema could look like this.

```python
from typing import ClassVar, Optional

from zenml.secret import register_secret_schema_class
from zenml.secret.base_secret import BaseSecretSchema

EXAMPLE_SECRET_SCHEMA_TYPE = "example"

@register_secret_schema_class
class ExampleSecretSchema(BaseSecretSchema):

    TYPE: ClassVar[str] = EXAMPLE_SECRET_SCHEMA_TYPE

    username: str
    password: str
    token: Optional[str]
```
