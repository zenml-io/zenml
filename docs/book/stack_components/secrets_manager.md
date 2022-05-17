---
description: Using secrets across your ZenML pipeline
---

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. ZenML provides you a Secret Manager as 
stack component to help manage and use these secrets for your pipeline runs.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](./introduction.md).  
{% endhint %}

## Base Abstraction

...

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
    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets."""
```

## List of available secrets managers

Out of the box, ZenML comes with a `LocalSecretsManager` implementation, which 
is a simple implementation for a local setup. This secrets manager simply saves 
secrets into a local yaml file with base64 encoding. This implementation is
not intended for production use.

For production use cases some more flavors can be found in specific 
`integrations` modules, such as the `GCPSecretsManager` in the 
`gcp_secrets_manager` integration and the `AWSSecretsManager` in the 
`aws` integration.

|                     | Flavor               | Integration         |
|---------------------|----------------------|---------------------|
| LocalSecretsManager | local                | `built-in`          |
| AWSSecretsManager   | aws                  | aws                 |
| GCPSecretsManager   | gcp_secrets_manager  | gcp_secrets_manager |

If you would like to see the available flavors for artifact stores, you can 
use the command:

```shell
zenml secrets-manager flavor list
```

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

