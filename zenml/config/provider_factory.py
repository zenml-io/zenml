from typing import Dict

from zenml.providers.base_provider import Provider

# TODO [LOW] This is unused, we should remove as design gets clearer.
class ProviderFactory:
    """Definition of ProviderFactory to track all providers.

    All providers (including custom providers) are to be
    registered here.
    """

    def __init__(self):
        self.providers: Dict = {}

    def get_providers(self) -> Dict:
        """Return all registered providers."""
        return self.providers

    def get_single_provider(self, key: Provider) -> Provider:
        """Return a single providers based on key."""
        return self.providers[key]

    def register_provider(self, key, provider_):
        """Register a provider with a key."""
        self.providers[key] = provider_


# Register the injections into the factory
wrapper_factory = ProviderFactory()
wrapper_factory.register_provider(Provider.provider_type, Provider)
provider_factory = ProviderFactory()
