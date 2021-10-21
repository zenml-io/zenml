Module zenml.orchestrators.local.local_orchestrator
===================================================

Classes
-------

`LocalOrchestrator(**values: Any)`
:   Orchestrator responsible for running pipelines locally.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.orchestrators.base_orchestrator.BaseOrchestrator
    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Methods

    `run(self, zenml_pipeline: BasePipeline, **pipeline_args)`
    :   Runs a pipeline locally.
        
        Args:
            zenml_pipeline: The pipeline to run.
            **pipeline_args: Unused kwargs to conform with base signature.