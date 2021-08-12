import types
from typing import Type

from playground.steps.base_step import BaseStep


def SimpleStep(func: types.FunctionType) -> Type:
    step_class = type(func.__name__,
                      (BaseStep,),
                      {"process": staticmethod(func)})

    return step_class
