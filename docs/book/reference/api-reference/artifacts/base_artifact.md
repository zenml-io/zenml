Module zenml.artifacts.base_artifact
====================================

Classes
-------

`BaseArtifact(mlmd_artifact_type: Optional[ml_metadata.proto.metadata_store_pb2.ArtifactType] = None)`
:   Base class for all ZenML artifacts.
    
    Every implementation of an artifact needs to inherit this class.
    
    While inheriting from this class there are a few things to consider:
    
    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    - TODO [MEDIUM]: Write about the materializers
    
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

    * tfx.types.artifact.Artifact
    * tfx.utils.json_utils.Jsonable
    * abc.ABC

    ### Descendants

    * zenml.artifacts.data_artifact.DataArtifact
    * zenml.artifacts.model_artifact.ModelArtifact

    ### Class variables

    `PROPERTIES`
    :

    `TYPE_NAME`
    :