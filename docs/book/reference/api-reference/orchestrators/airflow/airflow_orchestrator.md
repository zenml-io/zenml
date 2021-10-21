Module zenml.orchestrators.airflow.airflow_orchestrator
=======================================================

Classes
-------

`AirflowOrchestrator(**values: Any)`
:   Orchestrator responsible for running pipelines using Airflow.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.orchestrators.base_orchestrator.BaseOrchestrator
    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Methods

    `run(self, zenml_pipeline: BasePipeline, **kwargs)`
    :   Prepares the pipeline so it can be run in Airflow.
        
        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Unused argument to conform with base class signature.