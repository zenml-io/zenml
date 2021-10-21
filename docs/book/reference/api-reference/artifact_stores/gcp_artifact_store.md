Module zenml.artifact_stores.gcp_artifact_store
===============================================

Classes
-------

`GCPArtifactStore(**values: Any)`
:   Artifact Store for Google Cloud Storage based artifacts.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.artifact_stores.base_artifact_store.BaseArtifactStore
    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Class variables

    `path: str`
    :

    ### Static methods

    `must_be_gcs_path(v: str)`
    :   Validates that the path is a valid gcs path.