Module zenml.steps.step_decorator
=================================

Functions
---------

    
`step(*, name: str = None) ‑> Callable[..., zenml.steps.base_step.BaseStep]`
:   Outer decorator function for the creation of a ZenML step
    
    In order to be able work with parameters such as `name`, it features a
    nested decorator structure.
    
    Args:
        _func: Optional func from outside.
        name (required) the given name for the step.
    
    Returns:
        the inner decorator which creates the step class based on the
        ZenML BaseStep