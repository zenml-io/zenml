Module zenml.pipelines.base_pipeline
====================================

Classes
-------

`BasePipeline(*args, **kwargs)`
:   Base ZenML pipeline.

    ### Class variables

    `NAME`
    :

    `STEP_SPEC`
    :

    ### Instance variables

    `name: str`
    :   Name of pipeline is always equal to self.NAME

    `stack: zenml.stacks.base_stack.BaseStack`
    :   Returns the stack for this pipeline.

    `steps: Dict`
    :   Returns a dictionary of pipeline steps.

    ### Methods

    `connect(self, *args, **kwargs)`
    :   Function that connects inputs and outputs of the pipeline steps.

    `run(*args, **kwargs)`
    :   Inner decorator function.

`BasePipelineMeta(*args, **kwargs)`
:   Pipeline Metaclass responsible for validating the pipeline definition.

    ### Ancestors (in MRO)

    * builtins.type