from typing import Optional, Text
from uuid import uuid4

from pydantic import BaseSettings

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.config.utils import define_yaml_config_settings_source
from zenml.metadata.metadata_wrapper import BaseMetadataStore
from zenml.utils.path_utils import get_zenml_config_dir


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
    * Variables loaded from the secrets directory (not implemented yet).
    * The default field values.
    """

    provider_type: Text = "base"
    uuid: Text = str(uuid4())
    metadata_store: Optional[BaseMetadataStore]
    artifact_store: Optional[BaseArtifactStore]
    orchestrator: Optional[str]

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
                define_yaml_config_settings_source(
                    get_zenml_config_dir(), "test"
                ),
                file_secret_settings,
            )
