from typing import TYPE_CHECKING, Any, Dict

from zenml.core import mapping_utils
from zenml.core.base_component import BaseComponent
from zenml.core.mapping_utils import UUIDSourceTuple
from zenml.exceptions import AlreadyExistsException, DoesNotExistException
from zenml.io.utils import get_zenml_config_dir
from zenml.logger import get_logger
from zenml.stacks import BaseStack
from zenml.utils import source_utils
from zenml.utils.analytics_utils import (
    REGISTERED_ARTIFACT_STORE,
    REGISTERED_CONTAINER_REGISTRY,
    REGISTERED_METADATA_STORE,
    REGISTERED_ORCHESTRATOR,
    REGISTERED_STACK,
    track,
    track_event,
)

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.container_registries import BaseContainerRegistry
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.orchestrators import BaseOrchestrator

logger = get_logger(__name__)


class LocalService(BaseComponent):
    """Definition of a local service that keeps track of all ZenML
    components.
    """

    stacks: Dict[str, BaseStack] = {}
    active_stack_key: str = "local_stack"
    metadata_store_map: Dict[str, UUIDSourceTuple] = {}
    artifact_store_map: Dict[str, UUIDSourceTuple] = {}
    orchestrator_map: Dict[str, UUIDSourceTuple] = {}
    container_registry_map: Dict[str, UUIDSourceTuple] = {}

    _LOCAL_SERVICE_FILE_NAME = "zenservice.json"

    def __init__(self, repo_path: str, **kwargs: Any) -> None:
        """Initializes a LocalService instance.

        Args:
            repo_path: Path to the repository of this service.
        """
        serialization_dir = get_zenml_config_dir(repo_path)
        super().__init__(serialization_dir=serialization_dir, **kwargs)
        self._repo_path = repo_path
        for stack in self.stacks.values():
            stack._repo_path = repo_path

    def get_serialization_file_name(self) -> str:
        """Return the name of the file where object is serialized."""
        return self._LOCAL_SERVICE_FILE_NAME

    @property
    def metadata_stores(self) -> Dict[str, "BaseMetadataStore"]:
        """Returns all registered metadata stores."""
        from zenml.metadata_stores import BaseMetadataStore

        return mapping_utils.get_components_from_store(  # type: ignore[return-value] # noqa
            BaseMetadataStore._METADATA_STORE_DIR_NAME,
            self.metadata_store_map,
            self._repo_path,
        )

    @property
    def artifact_stores(self) -> Dict[str, "BaseArtifactStore"]:
        """Returns all registered artifact stores."""
        from zenml.artifact_stores import BaseArtifactStore

        return mapping_utils.get_components_from_store(  # type: ignore[return-value] # noqa
            BaseArtifactStore._ARTIFACT_STORE_DIR_NAME,
            self.artifact_store_map,
            self._repo_path,
        )

    @property
    def orchestrators(self) -> Dict[str, "BaseOrchestrator"]:
        """Returns all registered orchestrators."""
        from zenml.orchestrators import BaseOrchestrator

        return mapping_utils.get_components_from_store(  # type: ignore[return-value] # noqa
            BaseOrchestrator._ORCHESTRATOR_STORE_DIR_NAME,
            self.orchestrator_map,
            self._repo_path,
        )

    @property
    def container_registries(self) -> Dict[str, "BaseContainerRegistry"]:
        """Returns all registered container registries."""
        from zenml.container_registries import BaseContainerRegistry

        return mapping_utils.get_components_from_store(  # type: ignore[return-value] # noqa
            BaseContainerRegistry._CONTAINER_REGISTRY_DIR_NAME,
            self.container_registry_map,
            self._repo_path,
        )

    def get_active_stack_key(self) -> str:
        """Returns the active stack key."""
        return self.active_stack_key

    def set_active_stack_key(self, stack_key: str) -> None:
        """Sets the active stack key."""
        if stack_key not in self.stacks:
            raise DoesNotExistException(
                f"Unable to set active stack for key `{stack_key}` because no "
                f"stack is registered for this key. Available keys: "
                f"{set(self.stacks)}"
            )

        self.active_stack_key = stack_key
        self.update()

    def get_stack(self, key: str) -> BaseStack:
        """Return a single stack based on key.

        Args:
            key: Unique key of stack.

        Returns:
            Stack specified by key.
        """
        logger.debug(f"Fetching stack with key {key}")
        if key not in self.stacks:
            raise DoesNotExistException(
                f"Stack of key `{key}` does not exist. "
                f"Available keys: {list(self.stacks.keys())}"
            )
        return self.stacks[key]

    @track(event=REGISTERED_STACK)
    def register_stack(self, key: str, stack: BaseStack) -> None:
        """Register a stack.

        Args:
            key: Unique key for the stack.
            stack: Stack to be registered.
        """
        logger.debug(
            f"Registering stack with key {key}, details: " f"{stack.dict()}"
        )

        # Check if the individual components actually exist.
        # TODO [ENG-190]: Add tests to check cases of registering a stack with a
        #  non-existing individual component. We can also improve the error
        #  logging for the CLI while we're at it.
        self.get_orchestrator(stack.orchestrator_name)
        self.get_artifact_store(stack.artifact_store_name)
        self.get_metadata_store(stack.metadata_store_name)
        if stack.container_registry_name:
            self.get_container_registry(stack.container_registry_name)

        if key in self.stacks:
            raise AlreadyExistsException(
                message=f"Stack `{key}` already exists!"
            )

        # Add the mapping.
        self.stacks[key] = stack
        self.update()

    def delete_stack(self, key: str) -> None:
        """Delete a stack specified with a key.

        Args:
            key: Unique key of stack.
        """
        _ = self.get_stack(key)  # check whether it exists
        del self.stacks[key]
        self.update()
        logger.debug(f"Deleted stack with key: {key}.")
        logger.info(
            "Deleting a stack currently does not delete the underlying "
            "architecture of the stack. It just deletes the reference to it. "
            "Therefore please make sure to delete these resources on your "
            "own. Also, if this stack was the active stack, please make sure "
            "to set a not active stack via `zenml stack set`."
        )

    def get_artifact_store(self, key: str) -> "BaseArtifactStore":
        """Return a single artifact store based on key.

        Args:
            key: Unique key of artifact store.

        Returns:
            Stack specified by key.
        """
        logger.debug(f"Fetching artifact_store with key {key}")
        if key not in self.artifact_store_map:
            raise DoesNotExistException(
                f"Stack of key `{key}` does not exist. "
                f"Available keys: {list(self.artifact_store_map.keys())}"
            )
        return mapping_utils.get_component_from_key(  # type: ignore[return-value] # noqa
            key, self.artifact_store_map, self._repo_path
        )

    def register_artifact_store(
        self, key: str, artifact_store: "BaseArtifactStore"
    ) -> None:
        """Register an artifact store.

        Args:
            artifact_store: Artifact store to be registered.
            key: Unique key for the artifact store.
        """
        logger.debug(
            f"Registering artifact store with key {key}, details: "
            f"{artifact_store.dict()}"
        )
        if key in self.artifact_store_map:
            raise AlreadyExistsException(
                message=f"Artifact Store `{key}` already exists!"
            )

        # Add the mapping.
        artifact_store.update()
        source = source_utils.resolve_class(artifact_store.__class__)
        self.artifact_store_map[key] = UUIDSourceTuple(
            uuid=artifact_store.uuid, source=source
        )
        self.update()

        # Telemetry
        from zenml.core.component_factory import artifact_store_factory

        track_event(
            REGISTERED_ARTIFACT_STORE,
            {
                "type": artifact_store_factory.get_component_key(
                    artifact_store.__class__
                )
            },
        )

    def delete_artifact_store(self, key: str) -> None:
        """Delete an artifact_store.

        Args:
            key: Unique key of artifact_store.
        """
        s = self.get_artifact_store(key)  # check whether it exists
        s.delete()
        del self.artifact_store_map[key]
        self.update()
        logger.debug(f"Deleted artifact_store with key: {key}.")

    def get_metadata_store(self, key: str) -> "BaseMetadataStore":
        """Return a single metadata store based on key.

        Args:
            key: Unique key of metadata store.

        Returns:
            Metadata store specified by key.
        """
        logger.debug(f"Fetching metadata store with key {key}")
        if key not in self.metadata_store_map:
            raise DoesNotExistException(
                f"Metadata store of key `{key}` does not exist. "
                f"Available keys: {list(self.metadata_store_map.keys())}"
            )
        return mapping_utils.get_component_from_key(  # type: ignore[return-value] # noqa
            key, self.metadata_store_map, self._repo_path
        )

    def register_metadata_store(
        self, key: str, metadata_store: "BaseMetadataStore"
    ) -> None:
        """Register a metadata store.

        Args:
            metadata_store: Metadata store to be registered.
            key: Unique key for the metadata store.
        """
        logger.debug(
            f"Registering metadata store with key {key}, details: "
            f"{metadata_store.dict()}"
        )
        if key in self.metadata_store_map:
            raise AlreadyExistsException(
                message=f"Metadata store `{key}` already exists!"
            )

        # Add the mapping.
        metadata_store.update()
        source = source_utils.resolve_class(metadata_store.__class__)
        self.metadata_store_map[key] = UUIDSourceTuple(
            uuid=metadata_store.uuid, source=source
        )
        self.update()

        # Telemetry
        from zenml.core.component_factory import metadata_store_factory

        track_event(
            REGISTERED_METADATA_STORE,
            {
                "type": metadata_store_factory.get_component_key(
                    metadata_store.__class__
                )
            },
        )

    def delete_metadata_store(self, key: str) -> None:
        """Delete a metadata store.

        Args:
            key: Unique key of metadata store.
        """
        s = self.get_metadata_store(key)  # check whether it exists
        s.delete()
        del self.metadata_store_map[key]
        self.update()
        logger.debug(f"Deleted metadata store with key: {key}.")

    def get_orchestrator(self, key: str) -> "BaseOrchestrator":
        """Return a single orchestrator based on key.

        Args:
            key: Unique key of orchestrator.

        Returns:
            Orchestrator specified by key.
        """
        logger.debug(f"Fetching orchestrator with key {key}")
        if key not in self.orchestrator_map:
            raise DoesNotExistException(
                f"Orchestrator of key `{key}` does not exist. "
                f"Available keys: {list(self.orchestrator_map.keys())}"
            )
        return mapping_utils.get_component_from_key(  # type: ignore[return-value] # noqa
            key, self.orchestrator_map, self._repo_path
        )

    def register_orchestrator(
        self, key: str, orchestrator: "BaseOrchestrator"
    ) -> None:
        """Register an orchestrator.

        Args:
            orchestrator: Orchestrator to be registered.
            key: Unique key for the orchestrator.
        """
        logger.debug(
            f"Registering orchestrator with key {key}, details: "
            f"{orchestrator.dict()}"
        )
        if key in self.orchestrator_map:
            raise AlreadyExistsException(
                message=f"Orchestrator `{key}` already exists!"
            )

        # Add the mapping.
        orchestrator.update()
        source = source_utils.resolve_class(orchestrator.__class__)
        self.orchestrator_map[key] = UUIDSourceTuple(
            uuid=orchestrator.uuid, source=source
        )
        self.update()

        # Telemetry
        from zenml.core.component_factory import orchestrator_store_factory

        track_event(
            REGISTERED_ORCHESTRATOR,
            {
                "type": orchestrator_store_factory.get_component_key(
                    orchestrator.__class__
                )
            },
        )

    def delete_orchestrator(self, key: str) -> None:
        """Delete a orchestrator.

        Args:
            key: Unique key of orchestrator.
        """
        s = self.get_orchestrator(key)  # check whether it exists
        s.delete()
        del self.orchestrator_map[key]
        self.update()
        logger.debug(f"Deleted orchestrator with key: {key}.")

    def get_container_registry(self, key: str) -> "BaseContainerRegistry":
        """Return a single container registry based on key.

        Args:
            key: Unique key of a container registry.

        Returns:
            Container registry specified by key.
        """
        logger.debug(f"Fetching container registry with key {key}")
        if key not in self.container_registry_map:
            raise DoesNotExistException(
                f"Container registry of key `{key}` does not exist. "
                f"Available keys: {list(self.container_registry_map.keys())}"
            )
        return mapping_utils.get_component_from_key(  # type: ignore[return-value] # noqa
            key, self.container_registry_map, self._repo_path
        )

    @track(event=REGISTERED_CONTAINER_REGISTRY)
    def register_container_registry(
        self, key: str, container_registry: "BaseContainerRegistry"
    ) -> None:
        """Register a container registry.

        Args:
            container_registry: Container registry to be registered.
            key: Unique key for the container registry.
        """
        logger.debug(
            f"Registering container registry with key {key}, details: "
            f"{container_registry.dict()}"
        )
        if key in self.container_registry_map:
            raise AlreadyExistsException(
                message=f"Container registry `{key}` already exists!"
            )

        # Add the mapping.
        container_registry.update()
        source = source_utils.resolve_class(container_registry.__class__)
        self.container_registry_map[key] = UUIDSourceTuple(
            uuid=container_registry.uuid, source=source
        )
        self.update()

    def delete_container_registry(self, key: str) -> None:
        """Delete a container registry.

        Args:
            key: Unique key of the container registry.
        """
        container_registry = self.get_container_registry(key)
        container_registry.delete()
        del self.container_registry_map[key]
        self.update()
        logger.debug(f"Deleted container registry with key: {key}.")

    def delete(self) -> None:
        """Deletes the entire service. Dangerous operation"""
        for m in self.metadata_stores.values():
            m.delete()
        for a in self.artifact_stores.values():
            a.delete()
        for o in self.orchestrators.values():
            o.delete()
        for c in self.container_registries.values():
            c.delete()
        super().delete()
