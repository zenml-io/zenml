Module zenml.post_execution.pipeline_run
========================================

Classes
-------

`PipelineRunView(id_: int, name: str, executions: List[ml_metadata.proto.metadata_store_pb2.Execution], metadata_store: BaseMetadataStore)`
:   Post-execution pipeline run class which can be used to query
    steps and artifact information associated with a pipeline execution.
    
    Initializes a post-execution pipeline run object.
    
    In most cases `PipelineRunView` objects should not be created manually
    but retrieved from a `PipelineView` object instead.
    
    Args:
        id_: The context id of this pipeline run.
        name: The name of this pipeline run.
        executions: All executions associated with this pipeline run.
        metadata_store: The metadata store which should be used to fetch
            additional information related to this pipeline run.

    ### Instance variables

    `name: str`
    :   Returns the name of the pipeline run.

    `status: zenml.enums.ExecutionStatus`
    :   Returns the current status of the pipeline run.

    `steps: List[zenml.post_execution.step.StepView]`
    :   Returns all steps that were executed as part of this pipeline run.

    ### Methods

    `get_step(self, name: str) ‑> zenml.post_execution.step.StepView`
    :   Returns a step for the given name.
        
        Args:
            name: The name of the step to return.
        
        Raises:
            KeyError: If there is no step with the given name.

    `get_step_names(self) ‑> List[str]`
    :   Returns a list of all step names.