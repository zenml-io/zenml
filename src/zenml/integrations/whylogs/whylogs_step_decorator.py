#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import functools
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, overload

from zenml.integrations.whylogs.whylogs_context import WhylogsContext
from zenml.steps import BaseStep
from zenml.steps.step_context import StepContext
from zenml.steps.utils import STEP_INNER_FUNC_NAME

# step entrypoint type
F = TypeVar("F", bound=Callable[..., Any])

# step class type
S = TypeVar("S", bound=Type[BaseStep])


@overload
def enable_whylogs(
    _step: Type[BaseStep],
) -> S:
    """Type annotations for whylogs step decorator in case of no arguments."""
    ...


@overload
def enable_whylogs(
    *,
    project: Optional[str] = None,
    pipeline: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Callable[[Type[BaseStep]], Type[BaseStep]]:
    """Type annotations for whylogs step decorator in case of arguments."""
    ...


def enable_whylogs(
    _step: Optional[Type[BaseStep]] = None,
    *,
    project: Optional[str] = None,
    pipeline: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Union[Type[BaseStep], Callable[[Type[BaseStep]], Type[BaseStep]]]:
    """Decorator to enable whylogs profiling for a step function."""

    def whylogs_entrypoint(func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for a step entrypoint to enable whylogs"""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa

            for arg in args + tuple(kwargs.values()):
                if isinstance(arg, StepContext):
                    arg.__dict__["whylogs"] = WhylogsContext(arg)
                    break
            return func(*args, **kwargs)

        return wrapper

    def inner_decorator(_step: Type[BaseStep]) -> Type[BaseStep]:

        source_fn = getattr(_step, STEP_INNER_FUNC_NAME)
        return type(  # noqa
            _step.__name__,
            (_step,),
            {
                STEP_INNER_FUNC_NAME: staticmethod(
                    whylogs_entrypoint(source_fn)
                ),
                "__module__": _step.__module__,
            },
        )

    if _step is None:
        return inner_decorator
    else:
        return inner_decorator(_step)
