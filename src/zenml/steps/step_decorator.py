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
from typing import Any, Callable, Optional, Type, TypeVar, Union, overload

from zenml.steps.base_step import BaseStep
from zenml.steps.utils import PARAM_ENABLE_CACHE, STEP_INNER_FUNC_NAME

F = TypeVar("F", bound=Callable[..., Any])


@overload
def step(_func: F) -> Type[BaseStep]:
    """Type annotations for step decorator in case of no arguments."""
    ...


@overload
def step(
    *, name: Optional[str] = None, enable_cache: bool = True
) -> Callable[[F], Type[BaseStep]]:
    """Type annotations for step decorator in case of arguments."""
    ...


def step(
    _func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    enable_cache: bool = True
) -> Union[Type[BaseStep], Callable[[F], Type[BaseStep]]]:
    """Outer decorator function for the creation of a ZenML step

    In order to be able work with parameters such as `name`, it features a
    nested decorator structure.

    Args:
        _func: The decorated function.
        name: The name of the step. If left empty, the name of the decorated
            function will be used as a fallback.
        enable_cache: Whether to use caching or not.

    Returns:
        the inner decorator which creates the step class based on the
        ZenML BaseStep
    """

    def inner_decorator(func: F) -> Type[BaseStep]:
        """Inner decorator function for the creation of a ZenML Step

        Args:
          func: types.FunctionType, this function will be used as the
            "process" method of the generated Step

        Returns:
            The class of a newly generated ZenML Step.
        """
        step_name = name or func.__name__
        return type(  # noqa
            step_name,
            (BaseStep,),
            {
                STEP_INNER_FUNC_NAME: staticmethod(func),
                PARAM_ENABLE_CACHE: enable_cache,
                "__module__": func.__module__,
            },
        )

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
