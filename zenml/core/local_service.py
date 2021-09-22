import os
from pathlib import Path
from typing import Dict, List, Text, Type

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core import mapping_utils
from zenml.core.base_component import BaseComponent
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.metadata.base_metadata_store import BaseMetadataStore
from zenml.providers.base_provider import BaseProvider
from zenml.utils import path_utils

logger = get_logger(__name__)


class LocalService(BaseComponent):
    """Definition of a local service that keeps track of all ZenML
    components.
    """

    provider_map: Dict[Text, Type[BaseProvider]] = {}
    metadata_store_map: Dict[Text, Type[BaseMetadataStore]] = {}
    artifact_store_map: Dict[Text, Type[BaseArtifactStore]] = {}
    orchestrator_map: Dict[Text, Text] = {}

    _LOCAL_SERVICE_FILE_NAME = "zenservice.json"

    def get_serialization_dir(self) -> Text:
        """The local service stores everything in the zenml config dir."""
        return path_utils.get_zenml_config_dir()

    def get_serialization_file_name(self) -> Text:
        """Return the name of the file where object is serialized."""
        return self._LOCAL_SERVICE_FILE_NAME

    @property
    def providers(self) -> List[BaseProvider]:
        """Returns all registered providers."""
        store_dir = os.path.join(
            path_utils.get_zenml_config_dir(),
            BaseProvider._PROVIDER_STORE_DIR_NAME,
        )
        stores = []
        for fnames in path_utils.list_dir(store_dir, only_file_names=True):
            key = Path(fnames).stem
            stores.append(
                mapping_utils.get_component_from_key(key, self.provider_map)
            )
        return stores

    @property
    def metadata_stores(self) -> List[BaseMetadataStore]:
        """Returns all registered metadata stores."""
        store_dir = os.path.join(
            path_utils.get_zenml_config_dir(),
            BaseMetadataStore._METADATA_STORE_DIR_NAME,
        )
        stores = []
        for fnames in path_utils.list_dir(store_dir, only_file_names=True):
            key = Path(fnames).stem
            stores.append(
                mapping_utils.get_component_from_key(
                    key, self.metadata_store_map
                )
            )
        return stores

    @property
    def artifact_stores(self) -> List[BaseArtifactStore]:
        """Returns all registered artifact stores."""
        store_dir = os.path.join(
            path_utils.get_zenml_config_dir(),
            BaseArtifactStore._ARTIFACT_STORE_DIR_NAME,
        )
        stores = []
        for fnames in path_utils.list_dir(store_dir, only_file_names=True):
            key = Path(fnames).stem
            stores.append(
                mapping_utils.get_component_from_key(
                    key, self.artifact_store_map
                )
            )
        return stores

    @property
    def orchestrators(self) -> List[Text]:
        """Returns all registered orchestrators."""
        return []

    def get_provider(self, key: Text) -> BaseProvider:
        """Return a single provider based on key.

        Args:
            key: Unique key of provider.

        Returns:
            Provider specified by key.
        """
        logger.debug(f"Fetching provider with key {key}")
        if key not in self.provider_map:
            raise DoesNotExistException(
                f"Provider of key `{key}` does not exist. "
                f"Available keys: {self.provider_map.keys()}"
            )
        return mapping_utils.get_component_from_key(key, self.provider_map)

    def register_provider(self, provider: BaseProvider):
        """Register a provider.

        Args:
            provider: Provider to be registered.
        """
        logger.info(
            f"Registering provider with key {provider.key}, details: "
            f"{provider.dict()}"
        )

        # Add the mapping.
        provider.update()
        self.providers[provider.key] = provider.__class__
        self.update()

    def delete_provider(self, key: Text):
        """Delete a provider specified with a key.

        Args:
            key: Unique key of provider.
        """
        _ = self.get_provider(key)  # check whether it exists
        del self.provider_map[key]
        logger.info(f"Deleted provider with key: {key}.")

    def get_artifact_store(self, key: Text) -> BaseArtifactStore:
        """Return a single artifact store based on key.

        Args:
            key: Unique key of artifact store.

        Returns:
            Provider specified by key.
        """
        logger.debug(f"Fetching artifact_store with key {key}")
        if key not in self.artifact_store_map:
            raise DoesNotExistException(
                f"Provider of key `{key}` does not exist. "
                f"Available keys: {self.artifact_store_map.keys()}"
            )
        return mapping_utils.get_component_from_key(
            key, self.artifact_store_map
        )

    def register_artifact_store(self, artifact_store: BaseArtifactStore):
        """Register an artifact store.

        Args:
            artifact_store: Artifact store to be registered.
        """
        logger.info(
            f"Registering provider with key {artifact_store.key}, details: "
            f"{artifact_store.dict()}"
        )

        # Add the mapping.
        artifact_store.update()
        self.artifact_store_map[artifact_store.key] = artifact_store.__class__
        self.update()

    def delete_artifact_store(self, key: Text):
        """Delete a artifact_store.

        Args:
            key: Unique key of artifact_store.
        """
        _ = self.get_artifact_store(key)  # check whether it exists
        del self.artifact_store_map[key]
        logger.info(f"Deleted artifact_store with key: {key}.")
