Module zenml.metadata.mock_metadata_wrapper
===========================================

Classes
-------

`MockMetadataStore(**values: Any)`
:   Mock metadata store.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.metadata.base_metadata_store.BaseMetadataStore
    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Methods

    `get_tfx_metadata_config(self)`
    :   Return tfx metadata config for mock metadata store.