Module zenml.core.local_service
===============================

Classes
-------

`LocalService(**values: Any)`
:   Definition of a local service that keeps track of all ZenML
    components.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `artifact_store_map: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]`
    :

    `metadata_store_map: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]`
    :

    `orchestrator_map: Dict[str, zenml.core.mapping_utils.UUIDSourceTuple]`
    :

    `stacks: Dict[str, zenml.stacks.base_stack.BaseStack]`
    :

    ### Instance variables

    `artifact_stores: Dict[str, zenml.artifact_stores.base_artifact_store.BaseArtifactStore]`
    :   Returns all registered artifact stores.

    `metadata_stores: Dict[str, zenml.metadata.base_metadata_store.BaseMetadataStore]`
    :   Returns all registered metadata stores.

    `orchestrators: Dict[str, zenml.orchestrators.base_orchestrator.BaseOrchestrator]`
    :   Returns all registered orchestrators.

    ### Methods

    `delete(self)`
    :   Deletes the entire service. Dangerous operation

    `delete_artifact_store(self, key: str)`
    :   Delete an artifact_store.
        
        Args:
            key: Unique key of artifact_store.

    `delete_metadata_store(self, key: str)`
    :   Delete a metadata store.
        
        Args:
            key: Unique key of metadata store.

    `delete_orchestrator(self, key: str)`
    :   Delete a orchestrator.
        
        Args:
            key: Unique key of orchestrator.

    `delete_stack(self, key: str)`
    :   Delete a stack specified with a key.
        
        Args:
            key: Unique key of stack.

    `get_artifact_store(self, key: str) ‑> zenml.artifact_stores.base_artifact_store.BaseArtifactStore`
    :   Return a single artifact store based on key.
        
        Args:
            key: Unique key of artifact store.
        
        Returns:
            Stack specified by key.

    `get_metadata_store(self, key: str) ‑> zenml.metadata.base_metadata_store.BaseMetadataStore`
    :   Return a single metadata store based on key.
        
        Args:
            key: Unique key of metadata store.
        
        Returns:
            Metadata store specified by key.

    `get_orchestrator(self, key: str) ‑> zenml.orchestrators.base_orchestrator.BaseOrchestrator`
    :   Return a single orchestrator based on key.
        
        Args:
            key: Unique key of orchestrator.
        
        Returns:
            Orchestrator specified by key.

    `get_serialization_dir(self) ‑> str`
    :   The local service stores everything in the zenml config dir.

    `get_serialization_file_name(self) ‑> str`
    :   Return the name of the file where object is serialized.

    `get_stack(self, key: str) ‑> zenml.stacks.base_stack.BaseStack`
    :   Return a single stack based on key.
        
        Args:
            key: Unique key of stack.
        
        Returns:
            Stack specified by key.

    `register_artifact_store(*args, **kwargs)`
    :   Inner decorator function.

    `register_metadata_store(*args, **kwargs)`
    :   Inner decorator function.

    `register_orchestrator(*args, **kwargs)`
    :   Inner decorator function.

    `register_stack(*args, **kwargs)`
    :   Inner decorator function.