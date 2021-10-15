#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


import types
from typing import Callable, Type

from zenml.pipelines.base_pipeline import PIPELINE_INNER_FUNC_NAME, BasePipeline


def pipeline(
    _func: types.FunctionType = None, *, name: str = None
) -> Callable[..., BasePipeline]:
    """Outer decorator function for the creation of a ZenML pipeline

    In order to be able work with parameters such as "name", it features a
    nested decorator structure.

    Args:
        _func: Optional func from outside.
        name: str, the given name for the pipeline

    Returns:
        the inner decorator which creates the pipeline class based on the
        ZenML BasePipeline
    """

    def inner_decorator(func: types.FunctionType) -> Type:
        """Inner decorator function for the creation of a ZenML Pipeline

        Args:
          func: types.FunctionType, this function will be used as the
            "connect" method of the generated Pipeline

        Returns:
            the class of a newly generated ZenML Pipeline

        """
        return type(
            name if name else func.__name__,
            (BasePipeline,),
            {PIPELINE_INNER_FUNC_NAME: staticmethod(func)},
        )

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
