Module zenml.orchestrators.base_orchestrator
============================================

Classes
-------

`BaseOrchestrator(**values: Any)`
:   Base Orchestrator class to orchestrate ZenML pipelines.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * zenml.core.base_component.BaseComponent
    * pydantic.env_settings.BaseSettings
    * pydantic.main.BaseModel
    * pydantic.utils.Representation

    ### Descendants

    * zenml.orchestrators.airflow.airflow_orchestrator.AirflowOrchestrator
    * zenml.orchestrators.local.local_orchestrator.LocalOrchestrator

    ### Methods

    `get_serialization_dir(self) ‑> str`
    :   Gets the local path where artifacts are stored.

    `run(self, zenml_pipeline: BasePipeline, **kwargs)`
    :   Abstract method to run a pipeline. Overwrite this in subclasses
        with a concrete implementation on how to run the given pipeline.
        
        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Potential additional parameters used in subclass
                implementations.