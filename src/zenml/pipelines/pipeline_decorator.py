#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import (
    Callable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

from zenml.pipelines.base_pipeline import (
    INSTANCE_CONFIGURATION,
    PARAM_DOCKERIGNORE_FILE,
    PARAM_ENABLE_CACHE,
    PARAM_REQUIRED_INTEGRATIONS,
    PARAM_REQUIREMENTS,
    PARAM_REQUIREMENTS_FILE,
    PARAM_SECRETS,
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
    *,
    name: Optional[str] = None,
    enable_cache: bool = True,
    required_integrations: Sequence[str] = (),
    requirements_file: Optional[str] = None,
    requirements: Optional[Union[str, List[str]]] = None,
    dockerignore_file: Optional[str] = None,
    secrets: Optional[List[str]] = [],
) -> Callable[[F], Type[BasePipeline]]:
    """Type annotations for step decorator in case of arguments."""
    ...


def pipeline(
    _func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    enable_cache: bool = True,
    required_integrations: Sequence[str] = (),
    requirements_file: Optional[str] = None,
    requirements: Optional[Union[str, List[str]]] = None,
    dockerignore_file: Optional[str] = None,
    secrets: Optional[List[str]] = [],
) -> Union[Type[BasePipeline], Callable[[F], Type[BasePipeline]]]:
    """Outer decorator function for the creation of a ZenML pipeline

    In order to be able to work with parameters such as "name", it features a
    nested decorator structure.

    Args:
        _func: The decorated function.
        name: The name of the pipeline. If left empty, the name of the
            decorated function will be used as a fallback.
        enable_cache: Whether to use caching or not.
        required_integrations: Optional list of ZenML integrations that are
            required to run this pipeline. Run `zenml integration list` for
            a full list of available integrations.
        requirements_file: DEPRECATED: Optional path to a pip requirements file
        that contains requirements to run the pipeline. Please use
        'requirements' instead.
        requirements: Optional path to a requirements file or a list of requirements.
        dockerignore_file: Optional path to a dockerignore file to use when
            building docker images for running this pipeline.
            **Note**: If you pass a file, make sure it does not include the
            `.zen` directory as it is needed to run ZenML inside the container.

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
                PIPELINE_INNER_FUNC_NAME: staticmethod(func),  # type: ignore[arg-type] # noqa
                INSTANCE_CONFIGURATION: {
                    PARAM_ENABLE_CACHE: enable_cache,
                    PARAM_REQUIRED_INTEGRATIONS: required_integrations,
                    PARAM_REQUIREMENTS_FILE: requirements_file,
                    PARAM_REQUIREMENTS: requirements,
                    PARAM_DOCKERIGNORE_FILE: dockerignore_file,
                    PARAM_SECRETS: secrets,
                },
                "__module__": func.__module__,
                "__doc__": func.__doc__,
            },
        )

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
