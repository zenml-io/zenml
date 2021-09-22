from typing import Dict, Text, List, Optional

from zenml.core.base_component import BaseComponent
from zenml.config.constants import LOCAL_CONFIG_NAME
from zenml.core.utils import define_json_config_settings_source
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.providers.base_provider import BaseProvider
from zenml.providers.constants import DEFAULT_PROVIDER_KEY
from zenml.providers.local_provider import LocalProvider
from zenml.utils import path_utils

logger = get_logger(__name__)


def generate_default_providers() -> Dict[Text, BaseProvider]:
    """A default_factory method to generate default a provider dict."""
    return {DEFAULT_PROVIDER_KEY: LocalProvider()}


class ProviderManager(BaseComponent):
    """Definition of ProviderManager to track all providers.

    All providers (including custom providers) are to be
    registered here.

    A ZenML provider brings together an Metadata Store, an Artifact Store, and
    an Orchestrator, the trifecta of the environment required to run a ZenML
    pipeline. A ZenML provider also happens to be a pydantic `BaseSettings`
    class, which means that there are multiple ways to use it.

    * You can set it via env variables.
    * You can set it through the config yaml file.
    * You can set it in code by initializing an object of this class, and
    passing it to pipelines as a configuration.

    In the case where a value is specified for the same Settings field in
    multiple ways, the selected value is determined as follows (in descending
    order of priority):

    * Arguments passed to the Settings class initializer.
    * Environment variables, e.g. zenml_var as described above.
    * Variables loaded from a config yaml file.
    * The default field values.
    """

    provider_ids: Dict[Text, Text] = {}
    active_provider: Optional[Text] = None
    _providers: Dict[Text, BaseProvider] = {}

    @staticmethod
    def get_config_dir() -> Text:
        """Gets the config dir provider manager."""
        return path_utils.get_zenml_config_dir()

    @staticmethod
    def get_config_file_name() -> Text:
        """Gets the config name for provider manager."""
        return LOCAL_CONFIG_NAME

    def get_providers(self) -> List[BaseProvider]:
        """Return all registered providers."""
        logger.debug("Fetching providers..")
        return self.providers.values()

    def get_single_provider(self, key: Text) -> BaseProvider:
        """Return a single providers based on key.

        Args:
            key: Unique key of provider.

        Returns:
            Provider specified by key.
        """
        logger.debug(f"Fetching provider with key {key}")
        if key not in self.providers:
            raise DoesNotExistException(
                f"Provider of key `{key}` does not exist. "
                f"Available keys: {self.providers.keys()}"
            )
        return self.providers[key]

    def register_provider(self, key: Text, provider_: BaseProvider):
        """Register a provider with a key.

        Args:
            key: Unique key of provider.
        """
        logger.info(
            f"Registering provider with key {key}, details: {provider_.dict()}"
        )
        # name
        # resolve the type

        self.providers[key] = provider_

    def delete_provider(self, key: Text):
        """Delete a provider.

        Args:
            key: Unique key of provider.
        """
        _ = self.get_single_provider(key)  # check whether it exists
        del self.providers[key]
        logger.info(f"Deleted provider with key: {key}.")

    def get_active_provider(self) -> BaseProvider:
        """Test"""
        return

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                define_json_config_settings_source(
                    ProviderManager.get_config_dir(),
                    ProviderManager.get_config_file_name(),
                ),
            )
