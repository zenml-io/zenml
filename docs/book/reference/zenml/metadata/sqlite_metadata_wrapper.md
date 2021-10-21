Module zenml.metadata.sqlite_metadata_wrapper
=============================================

Classes
-------

`SQLiteMetadataStore(**data: Any)`
:   SQLite backend for ZenML metadata store.
    
    Constructor for MySQL MetadataStore for ZenML.

    ### Ancestors (in MRO)

    * zenml.metadata.base_metadata_store.BaseMetadataStore
    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `uri: str`
    :

    ### Static methods

    `uri_must_be_local(v)`
    :   Validator to ensure uri is local

    ### Methods

    `get_tfx_metadata_config(self)`
    :   Return tfx metadata config for sqlite metadata store.