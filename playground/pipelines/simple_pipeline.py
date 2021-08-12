import types
from typing import Type

from playground.pipelines.base_pipeline import BasePipeline


def SimplePipeline(func: types.FunctionType) -> Type:
    pipeline_class = type(func.__name__,
                          (BasePipeline,),
                          {"connect": staticmethod(func)})

    return pipeline_class
