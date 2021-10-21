Module zenml.core.base_component
================================

Classes
-------

`BaseComponent(**values: Any)`
:   Class definition for the base config.
    
    The base component class defines the basic serialization / deserialization
    of various components used in ZenML. The logic of the serialization /
    deserialization is as follows:
    
    * If a `uuid` is passed in, then the object is read from a file, so the
    constructor becomes a query for an object that is assumed to already been
    serialized.
    * If a 'uuid` is NOT passed, then a new object is created with the default
    args (and any other args that are passed), and therefore a fresh
    serialization takes place.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Descendants

    * zenml.artifact_stores.base_artifact_store.BaseArtifactStore
    * zenml.config.global_config.GlobalConfig
    * zenml.core.local_service.LocalService
    * zenml.metadata.base_metadata_store.BaseMetadataStore
    * zenml.orchestrators.base_orchestrator.BaseOrchestrator

    ### Class variables

    `Config`
    :   Configuration of settings.

    `uuid: Optional[uuid.UUID]`
    :

    ### Methods

    `delete(self)`
    :   Deletes the persisted state of this object.

    `get_serialization_dir(self) ‑> str`
    :   Return the dir where object is serialized.

    `get_serialization_file_name(self) ‑> str`
    :   Return the name of the file where object is serialized. This
        has a sane default in cases where uuid is not passed externally, and
        therefore reading from a serialize file is not an option for the table.
        However, we still this function to go through without an exception,
        therefore the sane default.

    `get_serialization_full_path(self) ‑> str`
    :   Returns the full path of the serialization file.

    `update(self)`
    :   Persist the current state of the component.
        
        Calling this will result in a persistent, stateful change in the
        system.