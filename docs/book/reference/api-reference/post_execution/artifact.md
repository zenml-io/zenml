Module zenml.post_execution.artifact
====================================

Classes
-------

`ArtifactView(id_: int, type_: str, uri: str, materializer: str)`
:   Post-execution artifact class which can be used to read
    artifact data that was created during a pipeline execution.
    
    Initializes a post-execution artifact object.
    
    In most cases `ArtifactView` objects should not be created manually but
    retrieved from a `StepView` via the `inputs` or `outputs` properties.
    
    Args:
        id_: The artifact id.
        type_: The type of this artifact.
        uri: Specifies where the artifact data is stored.
        materializer: Information needed to restore the materializer
            that was used to write this artifact.

    ### Instance variables

    `type: str`
    :   Returns the artifact type.

    `uri: str`
    :   Returns the URI where the artifact data is stored.

    ### Methods

    `read(self, output_data_type: Type, materializer_class: Optional[Type[zenml.materializers.base_materializer.BaseMaterializer]] = None) ‑> Any`
    :   Materializes the data stored in this artifact.
        
        Args:
            output_data_type: The datatype to which the materializer should
                read, will be passed to the materializers `handle_input` method.
            materializer_class: The class of the materializer that should be
                used to read the artifact data. If no materializer class is
                given, we use the materializer that was used to write the
                artifact during execution of the pipeline.
        
        Returns:
              The materialized data.