Module zenml.artifacts.data_artifact
====================================

Classes
-------

`DataArtifact(mlmd_artifact_type: Optional[ml_metadata.proto.metadata_store_pb2.ArtifactType] = None)`
:   Base class for any ZenML data artifact
    
    The custom properties include a property to hold split names
    
    Construct an instance of Artifact.
    
    Used by TFX internal implementation: create an empty Artifact with
    type_name and optional split info specified. The remaining info will be
    filled in during compiling and running time. The Artifact should be
    transparent to end users and should not be initiated directly by pipeline
    users.
    
    Args:
      mlmd_artifact_type: Proto message defining the underlying ArtifactType.
        Optional and intended for internal use.

    ### Ancestors (in MRO)

    * zenml.artifacts.base_artifact.BaseArtifact
    * tfx.types.artifact.Artifact
    * tfx.utils.json_utils.Jsonable
    * abc.ABC

    ### Class variables

    `PROPERTIES`
    :

    `TYPE_NAME`
    :