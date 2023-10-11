---
description: How to develop a custom secrets manager
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


## Base Abstraction

The secret manager acts as the one-stop shop for all the secrets to which your 
pipeline or stack components might need access. The `BaseSecretsManager` is 
implemented as follows:

```python
from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional, Type

from zenml.enums import StackComponentType
from zenml.secret.base_secret import BaseSecretSchema
from zenml.stack import StackComponent, StackComponentConfig, Flavor


class BaseSecretsManagerConfig(StackComponentConfig):
    """Base configuration for secrets managers."""

    SUPPORTS_SCOPING: ClassVar[bool] = False
    scope: SecretsManagerScope = SecretsManagerScope.COMPONENT
    namespace: Optional[str] = None

    ...

class BaseSecretsManager(StackComponent, ABC):
    """Base class for all ZenML secrets managers."""

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


class BaseSecretsManagerFlavor(Flavor):
    """Class for the `BaseSecretsManagerFlavor`."""
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the flavor."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type."""
        return StackComponentType.SECRETS_MANAGER

    @property
    def config_class(self) -> Type[BaseSecretsManagerConfig]:
        """Returns the config class."""
        return BaseSecretsManagerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseSecretsManager"]:
        """Implementation class for this flavor. """
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the [API docs](https://apidocs.zenml.io/latest/api_docs/secrets_managers/#zenml.secrets_managers.base_secrets_manager.BaseSecretsManager).
{% endhint %}

## Build your own custom secrets manager

If you want to create your own custom flavor for a secrets manager, you can 
follow the following steps:

1. Create a class which inherits from the `BaseSecretsManager` class and 
implement the `abstractmethod`s: `register_secret`, `get_secret`, 
`get_all_secret_keys`, `update_secret`, `delete_secret`, `delete_all_secrets`.
2. If you need to provide any configuration, create a class which inherits 
from the `BaseSecretsManagerConfig` class add your configuration parameters.
3. Bring both of the implementation and the configuration together by inheriting
from the `BaseSecretsManagerFlavor` class. Make sure that you give a `name`
to the flavor through its abstract property.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml secrets-manager flavor register <THE-SOURCE-PATH-OF-YOUR-SECRETS-MANAGER-FLAVOR>
```

{% hint style="warning" %}
It is important to draw attention to when and how these base abstractions are 
coming into play in a ZenML workflow.

- The **CustomSecretsManagerFlavor** class is imported and utilized upon the 
creation of the custom flavor through the CLI.
- The **CustomSecretsManagerConfig** class is imported when someone tries to 
register/update a stack component with this custom flavor. Especially, 
during the registration process of the stack component, the config will be used 
to validate the values given by the user. As `Config` object are inherently 
`pydantic` objects, you can also add your own custom validators here.
- The **CustomSecretsManager** only comes into play when the component is 
ultimately in use. 

The design behind this interaction lets us separate the configuration of the 
flavor from its implementation. This way we can register flavors and components 
even when the major dependencies behind their implementation are not installed
in our local setting (assuming the `CustomSecretsManagerFlavor` and the 
`CustomSecretsManagerConfig` are implemented in a different module/path than
the actual `CustomSecretsManager`).
{% endhint %}

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
