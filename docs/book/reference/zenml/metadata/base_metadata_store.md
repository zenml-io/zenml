Module zenml.metadata.base_metadata_store
=========================================

Classes
-------

`BaseMetadataStore(**values: Any)`
:   Metadata store base class to track metadata of zenml first class
    citizens.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Descendants

    * zenml.metadata.mock_metadata_wrapper.MockMetadataStore
    * zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore
    * zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore

    ### Instance variables

    `store`
    :   General property that hooks into TFX metadata store.

    ### Methods

    `get_pipeline(self, pipeline_name: str) ‑> Optional[zenml.post_execution.pipeline.PipelineView]`
    :   Returns a pipeline for the given name.

    `get_pipeline_run_steps(self, pipeline_run: zenml.post_execution.pipeline_run.PipelineRunView) ‑> Dict[str, zenml.post_execution.step.StepView]`
    :   Gets all steps for the given pipeline run.

    `get_pipeline_runs(self, pipeline: zenml.post_execution.pipeline.PipelineView) ‑> List[zenml.post_execution.pipeline_run.PipelineRunView]`
    :   Gets all runs for the given pipeline.

    `get_pipelines(self) ‑> List[zenml.post_execution.pipeline.PipelineView]`
    :   Returns a list of all pipelines stored in this metadata store.

    `get_serialization_dir(self) ‑> str`
    :   Gets the local path where artifacts are stored.

    `get_step_artifacts(self, step: zenml.post_execution.step.StepView) ‑> Tuple[Dict[str, zenml.post_execution.artifact.ArtifactView], Dict[str, zenml.post_execution.artifact.ArtifactView]]`
    :   Returns input and output artifacts for the given step.
        
        Args:
            step: The step for which to get the artifacts.
        
        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both OrderedDicts mapping artifact names
            to the input and output artifacts respectively.

    `get_step_status(self, step: zenml.post_execution.step.StepView) ‑> zenml.enums.ExecutionStatus`
    :

    `get_tfx_metadata_config(self)`
    :   Return tfx metadata config.