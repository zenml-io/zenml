#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Utilities for getting the source code of objects."""
import hashlib
import inspect
import sys
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import (
    Any,
    Callable,
    Type,
    Union,
)

from zenml.environment import Environment


def get_source_code(value: Any) -> str:
    """Returns the source code of an object.

    If executing within a IPython kernel environment, then this monkey-patches
    `inspect` module temporarily with a workaround to get source from the cell.

    Args:
        value: object to get source from.

    Returns:
        Source code of object.
    """
    if Environment.in_notebook():
        # Monkey patch inspect.getfile temporarily to make getsource work.
        # Source: https://stackoverflow.com/questions/51566497/
        def _new_getfile(
            object: Any,
            _old_getfile: Callable[
                [
                    Union[
                        ModuleType,
                        Type[Any],
                        MethodType,
                        FunctionType,
                        TracebackType,
                        FrameType,
                        CodeType,
                        Callable[..., Any],
                    ]
                ],
                str,
            ] = inspect.getfile,
        ) -> Any:
            if not inspect.isclass(object):
                return _old_getfile(object)

            # Lookup by parent module (as in current inspect)
            if hasattr(object, "__module__"):
                object_ = sys.modules.get(object.__module__)
                if hasattr(object_, "__file__"):
                    return object_.__file__  # type: ignore[union-attr]

            # If parent module is __main__, lookup by methods
            for _, member in inspect.getmembers(object):
                if (
                    inspect.isfunction(member)
                    and object.__qualname__ + "." + member.__name__
                    == member.__qualname__
                ):
                    return inspect.getfile(member)
            else:
                raise TypeError(f"Source for {object!r} not found.")

        # Monkey patch, compute source, then revert monkey patch.
        _old_getfile = inspect.getfile
        inspect.getfile = _new_getfile
        try:
            src = inspect.getsource(value)
        finally:
            inspect.getfile = _old_getfile
    else:
        # Use standard inspect if running outside a notebook
        src = inspect.getsource(value)
    return src


def get_hashed_source_code(value: Any) -> str:
    """Returns a hash of the objects source code.

    Args:
        value: object to get source from.

    Returns:
        Hash of source code.

    Raises:
        TypeError: If unable to compute the hash.
    """
    try:
        source_code = get_source_code(value)
    except TypeError:
        raise TypeError(
            f"Unable to compute the hash of source code of object: {value}."
        )
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()
