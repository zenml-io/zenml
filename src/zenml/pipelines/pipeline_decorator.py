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
from typing import Callable, Optional, Type, TypeVar, Union, overload

from zenml.pipelines.base_pipeline import (
    PARAM_ENABLE_CACHE,
    PIPELINE_INNER_FUNC_NAME,
    BasePipeline,
)

F = TypeVar("F", bound=Callable[..., None])


@overload
def pipeline(_func: F) -> Type[BasePipeline]:
    """Type annotations for pipeline decorator in case of no arguments."""
    ...


@overload
def pipeline(
    *, name: Optional[str] = None, enable_cache: bool = True
) -> Callable[[F], Type[BasePipeline]]:
    """Type annotations for step decorator in case of arguments."""
    ...


def pipeline(
    _func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    enable_cache: bool = True
) -> Union[Type[BasePipeline], Callable[[F], Type[BasePipeline]]]:
    """Outer decorator function for the creation of a ZenML pipeline

    In order to be able work with parameters such as "name", it features a
    nested decorator structure.

    Args:
        _func: The decorated function.
        name: The name of the pipeline. If left empty, the name of the
            decorated function will be used as a fallback.
        enable_cache: Whether to use caching or not.

    Returns:
        the inner decorator which creates the pipeline class based on the
        ZenML BasePipeline
    """

    def inner_decorator(func: F) -> Type[BasePipeline]:
        """Inner decorator function for the creation of a ZenML Pipeline

        Args:
          func: types.FunctionType, this function will be used as the
            "connect" method of the generated Pipeline

        Returns:
            the class of a newly generated ZenML Pipeline

        """
        return type(  # noqa
            name if name else func.__name__,
            (BasePipeline,),
            {
                PIPELINE_INNER_FUNC_NAME: staticmethod(func),
                PARAM_ENABLE_CACHE: enable_cache,
            },
        )

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
