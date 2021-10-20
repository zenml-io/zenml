Module zenml.artifact_stores.base_artifact_store
================================================
Definition of an Artifact Store

Classes
-------

`BaseArtifactStore(**values: Any)`
:   Base class for all ZenML Artifact Store.
    
    Every ZenML Artifact Store should override this class.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Descendants

    * zenml.artifact_stores.gcp_artifact_store.GCPArtifactStore
    * zenml.artifact_stores.local_artifact_store.LocalArtifactStore

    ### Class variables

    `path: str`
    :

    ### Static methods

    `get_component_name_from_uri(artifact_uri: str) ‑> str`
    :   Gets component name from artifact URI.
        
        Args:
          artifact_uri: URI to artifact.
        
        Returns:
            Name of the component (str).

    ### Methods

    `get_serialization_dir(self)`
    :   Gets the local path where artifacts are stored.

    `resolve_uri_locally(self, artifact_uri: str, path: str = None) ‑> str`
    :   Takes a URI that points within the artifact store, downloads the
        URI locally, then returns local URI.
        
        Args:
          artifact_uri: uri to artifact.
          path: optional path to download to. If None, is inferred.
        
        Returns:
            Locally resolved uri (str).