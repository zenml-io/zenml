Module zenml.post_execution.pipeline
====================================

Classes
-------

`PipelineView(id_: int, name: str, metadata_store: BaseMetadataStore)`
:   Post-execution pipeline class which can be used to query
    pipeline-related information from the metadata store.
    
    Initializes a post-execution pipeline object.
    
    In most cases `PipelineView` objects should not be created manually
    but retrieved using the `get_pipelines()` method of a
    `zenml.core.repo.Repository` instead.
    
    Args:
        id_: The context id of this pipeline.
        name: The name of this pipeline.
        metadata_store: The metadata store which should be used to fetch
            additional information related to this pipeline.

    ### Instance variables

    `name: str`
    :   Returns the name of the pipeline.

    ### Methods

    `get_runs(self) ‑> List[zenml.post_execution.pipeline_run.PipelineRunView]`
    :   Returns all stored runs of this pipeline.
        
        The runs are returned in chronological order, so the latest
        run will be the last element in this list.