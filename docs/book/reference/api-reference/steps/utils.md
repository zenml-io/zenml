Module zenml.steps.utils
========================
The collection of utility functions/classes are inspired by their original
implementation of the Tensorflow Extended team, which can be found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental
/decorators.py

This version is heavily adjusted to work with the Pipeline-Step paradigm which
is proposed by ZenML.

Functions
---------

    
`do_types_match(type_a: Type, type_b: Type) ‑> bool`
:   Check whether type_a and type_b match.
    
    Args:
        type_a: First Type to check.
        type_b: Second Type to check.
    
    Returns:
        True if types match, otherwise False.

    
`generate_component(step) ‑> Callable[..., Any]`
:   Utility function which converts a ZenML step into a TFX Component
    
    Args:
        step: a ZenML step instance
    
    Returns:
        component: the class of the corresponding TFX component