from typing import Text

from pydantic import BaseSettings

from zenml.enums import ProviderTypes


class BaseProvider(BaseSettings):
    """Base provider for ZenML.

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

    provider_type: ProviderTypes = ProviderTypes.base
    metadata_store_name: Text
    artifact_store_name: Text
    orchestrator_name: Text

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_provider_"
