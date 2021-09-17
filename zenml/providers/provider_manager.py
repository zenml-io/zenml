from typing import Dict, Text

from zenml.config.base_config import BaseConfig
from zenml.config.constants import LOCAL_CONFIG_DIR_NAME, LOCAL_CONFIG_NAME
from zenml.providers.base_provider import BaseProvider
from zenml.providers.local_provider import LocalProvider


class ProviderManager(BaseConfig):
    """Definition of ProviderManager to track all providers.

    All providers (including custom providers) are to be
    registered here.
    """

    providers: Dict = {LocalProvider().provider_type: LocalProvider}
    active_provider_key: Text = LocalProvider().provider_type

    def get_config_dir(self) -> Text:
        """Gets the config dir provider manager."""
        return LOCAL_CONFIG_DIR_NAME

    def get_config_file_name(self) -> Text:
        """Gets the config name for provider manager."""
        return LOCAL_CONFIG_NAME

    def get_providers(self) -> Dict:
        """Return all registered providers."""
        return self.providers

    def get_single_provider(self, key: BaseProvider) -> BaseProvider:
        """Return a single providers based on key."""
        return self.providers[key]

    def register_provider(self, key, provider_):
        """Register a provider with a key."""
        self.providers[key] = provider_
