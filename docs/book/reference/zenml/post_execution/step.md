Module zenml.post_execution.step
================================

Classes
-------

`StepView(id_: int, name: str, parameters: Dict[str, Any], metadata_store: BaseMetadataStore)`
:   Post-execution step class which can be used to query
    artifact information associated with a pipeline step.
    
    Initializes a post-execution step object.
    
    In most cases `StepView` objects should not be created manually
    but retrieved from a `PipelineRunView` object instead.
    
    Args:
        id_: The execution id of this step.
        name: The name of this step.
        parameters: Parameters that were used to run this step.
        metadata_store: The metadata store which should be used to fetch
            additional information related to this step.

    ### Instance variables

    `inputs: List[zenml.post_execution.artifact.ArtifactView]`
    :   Returns a list of input artifacts that were used to run this step.
        
        These artifacts are in the same order as defined in the signature of
        the step function.

    `name: str`
    :   Returns the step name.
        
        This name is equal to the name argument passed to the @step decorator
        or the actual function name if no explicit name was given.
        
        Examples:
            # the step name will be "my_step"
            @step(name="my_step")
            def my_step_function(...)
        
            # the step name will be "my_step_function"
            @step
            def my_step_function(...)

    `outputs: List[zenml.post_execution.artifact.ArtifactView]`
    :   Returns a list of output artifacts that were written by this step.
        
        These artifacts are in the same order as defined in the signature of
        the step function.

    `parameters: Dict[str, Any]`
    :   The parameters used to run this step.

    `status: zenml.enums.ExecutionStatus`
    :   Returns the current status of the step.

    ### Methods

    `get_input(self, name: str) ‑> zenml.post_execution.artifact.ArtifactView`
    :   Returns an input artifact for the given name.
        
        Args:
            name: The name of the input artifact to return.
        
        Raises:
            KeyError: If there is no input artifact with the given name.

    `get_input_names(self) ‑> List[str]`
    :   Returns a list of all input artifact names.

    `get_output(self, name: str) ‑> zenml.post_execution.artifact.ArtifactView`
    :   Returns an output artifact for the given name.
        
        Args:
            name: The name of the output artifact to return.
        
        Raises:
            KeyError: If there is no output artifact with the given name.

    `get_output_names(self) ‑> List[str]`
    :   Returns a list of all output artifact names.
        
        If a step only has a single output, it will have the
        default name `output`.