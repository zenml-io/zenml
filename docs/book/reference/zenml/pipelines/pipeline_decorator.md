Module zenml.pipelines.pipeline_decorator
=========================================

Functions
---------

    
`pipeline(*, name: str = None, enable_cache: bool = True) ‑> Callable[..., Type[zenml.pipelines.base_pipeline.BasePipeline]]`
:   Outer decorator function for the creation of a ZenML pipeline
    
    In order to be able work with parameters such as "name", it features a
    nested decorator structure.
    
    Args:
        _func: Optional func from outside.
        name: str, the given name for the pipeline
        enable_cache: Whether to use cache or not.
    
    Returns:
        the inner decorator which creates the pipeline class based on the
        ZenML BasePipeline