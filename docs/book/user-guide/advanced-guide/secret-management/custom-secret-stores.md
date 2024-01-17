---
description: Learning how to develop a custom secret store.
---

# Create a custom secret store

The secrets store acts as the one-stop shop for all the secrets to which your pipeline or stack components might need
access. The secrets store interface implemented by all available secrets store back-ends is defined in
the `zenml.zen_stores.secrets_stores.secrets_store_interface` core module and looks more or less like this:

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
    def create_secret(
        self,
        secret: SecretRequest,
    ) -> SecretResponse:
        """Creates a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            KeyError: if the user or workspace does not exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
            ValueError: if the secret is invalid.
        """

    @abstractmethod
    def get_secret(
        self, secret_id: UUID, hydrate: bool = True
    ) -> SecretResponse:
        """Get a secret with a given name.

        Args:
            secret_id: ID of the secret.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist.
        """

    @abstractmethod
    def list_secrets(
        self, secret_filter_model: SecretFilter, hydrate: bool = False
    ) -> Page[SecretResponse]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.
        """

    @abstractmethod
    def update_secret(
        self,
        secret_id: UUID,
        secret_update: SecretUpdate,
    ) -> SecretResponse:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).

        If the update includes a change of name or scope, the scoping rules
        enforced in the secrets store are used to validate the update:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
            ValueError: if the secret is invalid.
        """

    @abstractmethod
    def delete_secret(self, secret_id: UUID) -> None:
        """Deletes a secret.

        Args:
            secret_id: The ID of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
        """
```

{% hint style="info" %}
This is a slimmed-down version of the real interface which aims to highlight the abstraction layer. In order to see the
full definition and get the complete docstrings, please check
the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-zen\_stores/#zenml.zen\_stores.secrets\_stores.secrets\_store\_interface.SecretsStoreInterface)
.
{% endhint %}

#### Build your own custom secrets store

If you want to create your own custom secrets store implementation, you can follow the following steps:

1. Create a class that inherits from the `zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore` base
   class and implements the `abstractmethod`s shown in the interface above. Use `SecretsStoreType.CUSTOM` as the `TYPE`
   value for your secrets store class.
2. If you need to provide any configuration, create a class that inherits from the `SecretsStoreConfiguration` class and
   add your configuration parameters there. Use that as the `CONFIG_TYPE` value for your secrets store class.
3. To configure the ZenML server to use your custom secrets store, make sure your code is available in the container
   image that is used to run the ZenML server. Then, use environment variables or helm chart values to configure the
   ZenML server to use your custom secrets store, as covered in
   the [deployment guide](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
