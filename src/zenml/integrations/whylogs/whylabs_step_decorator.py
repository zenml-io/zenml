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
"""Implementation of the Whylabs step decorator."""

import functools
import os
from typing import Any, Callable, Optional, Type, TypeVar, Union, cast, overload

from zenml.steps import BaseStep
from zenml.steps.utils import STEP_INNER_FUNC_NAME

WHYLABS_LOGGING_ENABLED_ENV = "WHYLABS_LOGGING_ENABLED"
WHYLABS_DATASET_ID_ENV = "WHYLABS_DATASET_ID"

# step entrypoint type
F = TypeVar("F", bound=Callable[..., Any])

# step class type
S = TypeVar("S", bound=Type[BaseStep])


@overload
def enable_whylabs(
    _step: S,
) -> S:
    ...


@overload
def enable_whylabs(
    *,
    dataset_id: Optional[str] = None,
) -> Callable[[S], S]:
    ...


def enable_whylabs(
    _step: Optional[S] = None,
    *,
    dataset_id: Optional[str] = None,
) -> Union[S, Callable[[S], S]]:
    """Decorator to enable Whylabs profiling for a step function.

    Apply this decorator to a ZenML pipeline step to enable Whylabs profiling.

    Note that you also need to have a whylogs Data Validator part of your active
    stack with the Whylabs credentials configured for this to have effect.

    All the whylogs data profile views returned by the step will automatically
    be uploaded to the Whylabs platform if the active whylogs Data Validator
    component is configured with Whylabs credentials, e.g.:

    ```python
    import whylogs as why
    from whylogs.core import DatasetProfileView
    from zenml.integrations.whylogs.whylabs_step_decorator import enable_whylabs

    @enable_whylabs(dataset_id="my_model")
    @step
    def data_loader() -> Output(data=pd.DataFrame, profile=DatasetProfileView,):
        ...
        data = pd.DataFrame(...)
        results = why.log(pandas=dataset)
        profile = results.profile()
        ...
        return data, profile.view()
    ```

    You can also use this decorator with our class-based API like so:
    ```
    @enable_whylabs(dataset_id="my_model")
    class DataLoader(BaseStep):
        def entrypoint(self) -> Output(data=pd.DataFrame, profile=DatasetProfileView,):
            ...
    ```

    Args:
        _step: The decorated step class.
        dataset_id: Optional dataset ID to use for the uploaded profile(s)

    Returns:
        the inner decorator which enhances the input step class with Whylabs
        profiling functionality
    """

    def inner_decorator(_step: S) -> S:
        source_fn = getattr(_step, STEP_INNER_FUNC_NAME)
        new_entrypoint = whylabs_entrypoint(dataset_id)(source_fn)
        if _step._created_by_functional_api():
            # If the step was created by the functional API, the old entrypoint
            # was a static method -> make sure the new one is as well
            new_entrypoint = staticmethod(new_entrypoint)

        setattr(_step, STEP_INNER_FUNC_NAME, new_entrypoint)
        return _step

    if _step is None:
        return inner_decorator
    else:
        return inner_decorator(_step)


def whylabs_entrypoint(
    dataset_id: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator for a step entrypoint to enable Whylabs logging.

    Apply this decorator to a ZenML pipeline step to enable Whylabs profiling.

    Note that you also need to have a whylogs Data Validator part of your active
    stack with the Whylabs credentials configured for this to have effect.

    All the whylogs data profile views returned by the step will automatically
    be uploaded to the Whylabs platform if the active whylogs Data Validator
    component is configured with Whylabs credentials, e.g.:

    .. highlight:: python
    .. code-block:: python

        import whylogs as why
        from whylogs.core import DatasetProfileView
        from zenml.integrations.whylogs.whylabs_step_decorator import whylabs_entrypoint

        @step
        @whylabs_entrypoint(dataset_id="my_model")
        def data_loader() -> Output(data=pd.DataFrame, profile=DatasetProfileView,):
            ...
            data = pd.DataFrame(...)
            results = why.log(pandas=dataset)
            profile = results.profile()
            ...
            return data, profile.view()

    Args:
        dataset_id: Optional dataset ID to use for the uploaded profile(s)

    Returns:
        the input function enhanced with Whylabs profiling functionality
    """

    def inner_decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
            os.environ[WHYLABS_LOGGING_ENABLED_ENV] = "true"
            if dataset_id:
                os.environ[WHYLABS_DATASET_ID_ENV] = dataset_id
            try:
                return func(*args, **kwargs)
            finally:
                del os.environ[WHYLABS_LOGGING_ENABLED_ENV]
                if dataset_id:
                    del os.environ[WHYLABS_DATASET_ID_ENV]

        return cast(F, wrapper)

    return inner_decorator
