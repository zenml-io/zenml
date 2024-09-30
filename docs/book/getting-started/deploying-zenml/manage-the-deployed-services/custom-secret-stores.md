---
description: Learning how to develop a custom secret store.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Custom secret stores

The secrets store acts as the one-stop shop for all the secrets to which your pipeline or stack components might need access. It is responsible for storing, updating and deleting _only the secrets values_ for ZenML secrets, while the ZenML secret metadata is stored in the SQL database. The secrets store interface implemented by all available secrets store back-ends is defined in the `zenml.zen_stores.secrets_stores.secrets_store_interface` core module and looks more or less like this:

```python
class SecretsStoreInterface(ABC):
    """ZenML secrets store interface.

    All ZenML secrets stores must implement the methods in this interface.
    """

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the secrets store.

        This method is called immediately after the secrets store is created.
        It should be used to set up the backend (database, connection etc.).
        """

    # ---------
    # Secrets
    # ---------

    @abstractmethod
    def store_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Store secret values for a new secret.

        Args:
            secret_id: ID of the secret.
            secret_values: Values for the secret.
        """

    @abstractmethod
    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """

    @abstractmethod
    def update_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Updates secret values for an existing secret.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_values: The new secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """

    @abstractmethod
    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
        """
```

{% hint style="info" %}
This is a slimmed-down version of the real interface which aims to highlight the abstraction layer. In order to see the full definition and get the complete docstrings, please check the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-zen\_stores/#zenml.zen\_stores.secrets\_stores.secrets\_store\_interface.SecretsStoreInterface) .
{% endhint %}

## Build your own custom secrets store

If you want to create your own custom secrets store implementation, you can follow the following steps:

1. Create a class that inherits from the `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore` base class and implements the `abstractmethod`s shown in the interface above. Use `SecretsStoreType.CUSTOM` as the `TYPE` value for your secrets store class.
2. If you need to provide any configuration, create a class that inherits from the `SecretsStoreConfiguration` class and add your configuration parameters there. Use that as the `CONFIG_TYPE` value for your secrets store class.
3. To configure the ZenML server to use your custom secrets store, make sure your code is available in the container image that is used to run the ZenML server. Then, use environment variables or helm chart values to configure the ZenML server to use your custom secrets store, as covered in the [deployment guide](../README.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
