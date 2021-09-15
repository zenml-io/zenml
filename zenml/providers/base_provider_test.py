import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseSettings

from zenml.artifacts.artifact_store import BaseArtifactStore
from zenml.metadata.metadata_wrapper import BaseMetadataStore
from zenml.utils.path_utils import CONFIG_NAME, get_zenml_dir


def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a JSON file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`

    Args:
        settings (BaseSettings): BaseSettings from pydantic.
    """
    encoding = settings.__config__.env_file_encoding
    full_path = Path(get_zenml_dir()) / CONFIG_NAME
    if full_path.exists():
        return json.loads(full_path.read_text(encoding))
    return {}


class BaseProvider(BaseSettings):
    """Base provider for ZenML.

    A ZenML provider brings together an Metadata Store, an Artifact Store, and
    an Orchestrator, the trifecta of the environment required to run a ZenML
    pipeline. A ZenML provider also happens to be a pydantic `BaseSettings`
    class, which means that there are multiple ways to use it.

    * You can set it via env variables.
    * You can set it through the zenml_config.json file.
    * You can set it in code by initializing an object of this class, and
    passing it to pipelines as a configuration.

    In the case where a value is specified for the same Settings field in
    multiple ways, the selected value is determined as follows (in descending
    order of priority):

    * Arguments passed to the Settings class initialiser.
    * Environment variables, e.g. zenml_var as described above.
    * Variables loaded from a zenml_config.json file.
    * Variables loaded from the secrets directory (not implemented yet).
    * The default field values.
    """

    provider_type: str = "base"
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
                json_config_settings_source,
                file_secret_settings,
            )
