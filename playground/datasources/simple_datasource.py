import types
from typing import Type

from playground.datasources.base_datasource import BaseDatasource


def SimpleDatasource(func: types.FunctionType) -> Type:
    datasource_class = type(func.__name__,
                            (BaseDatasource,),
                            {"ingest": staticmethod(func)})

    return datasource_class
