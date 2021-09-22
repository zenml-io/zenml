from typing import Text

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core.base_component import BaseComponent
from zenml.enums import ProviderTypes
from zenml.metadata.base_metadata_store import BaseMetadataStore


class BaseProvider(BaseComponent):
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

    name: Text
    provider_type: ProviderTypes = ProviderTypes.base
    metadata_store_id: Text = ""
    artifact_store_id: Text = ""
    orchestrator_id: Text = ""
    _PROVIDER_STORE_DIR_NAME = "providers"

    @property
    def metadata_store(self) -> BaseMetadataStore:
        return self._metadata_store

    @property
    def artifact_store(self) -> BaseArtifactStore:
        return self._artifact_store

    @property
    def orchestrator(self) -> Text:
        return self._orchestrator

    @classmethod
    def get_properties(cls):
        return [
            prop
            for prop in dir(cls)
            if isinstance(getattr(cls, prop), property)
            and prop not in ("__values__", "fields")
        ]

    def get_serialization_dir(self) -> Text:
        """Return the dir where object is serialized."""
        return ""

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_provider_"
