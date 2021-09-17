from typing import Dict, Text
from uuid import uuid4

from pydantic import Field

from zenml.config.base_config import BaseConfig
from zenml.config.constants import LOCAL_CONFIG_NAME
from zenml.config.utils import define_yaml_config_settings_source
from zenml.providers.base_provider import BaseProvider
from zenml.providers.local_provider import LocalProvider
from zenml.utils.path_utils import get_zenml_config_dir


def generate_default_providers():
    """A default_factory method to generate default a provider dict."""
    return {str(uuid4()): LocalProvider()}


class ProviderManager(BaseConfig):
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
    * Variables loaded from the secrets directory (not implemented yet).
    * The default field values.
    """

    providers: Dict = Field(default_factory=generate_default_providers)
    active_provider_key: Text = LocalProvider().provider_type

    @staticmethod
    def get_config_dir() -> Text:
        """Gets the config dir provider manager."""
        return get_zenml_config_dir()

    @staticmethod
    def get_config_file_name() -> Text:
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
                define_yaml_config_settings_source(
                    ProviderManager.get_config_dir(),
                    ProviderManager.get_config_file_name(),
                ),
                env_settings,
            )


pm = ProviderManager()
print(pm)
