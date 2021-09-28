import types
from typing import Type

from zenml.steps.base_step import BaseStep


def SimpleStep(func: types.FunctionType) -> Type:
    """

    Args:
      func: types.FunctionType:

    Returns:

    """
    step_class = type(
        func.__name__, (BaseStep,), {"process": staticmethod(func)}
    )

    return step_class
