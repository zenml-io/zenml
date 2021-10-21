Module zenml.steps.base_step_config
===================================

Classes
-------

`BaseStepConfig(**data: Any)`
:   Base configuration class to pass execution params into a step.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises ValidationError if the input data cannot be parsed to form a valid model.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel
    * pydantic.utils.Representation