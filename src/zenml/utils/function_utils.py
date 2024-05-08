#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utility functions for python functions."""

import inspect
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, List, TypeVar

import click

from zenml.utils.string_utils import random_str

F = TypeVar("F", bound=Callable[..., None])

_CLI_WRAPPED_SCRIPT_TEMPLATE = """
from zenml.utils.function_utils import _cli_wrapped_function

import sys
sys.path.append("{func_path}")
from {func_module} import {func_name} as func_to_wrap

func = _cli_wrapped_function(func_to_wrap)

if __name__=="__main__":
    func()
"""
_ALLOWED_TYPES = (str, int, float, bool)
_ALLOWED_COLLECTIONS = (tuple,)


def _cli_arg_name(arg_name: str) -> str:
    return arg_name.replace("_", "-")


def _is_valid_collection_arg(arg_type: Any) -> bool:
    if getattr(arg_type, "__origin__", None) in _ALLOWED_COLLECTIONS:
        if arg_type.__args__[0] not in _ALLOWED_TYPES:
            return False
        return True
    return False


def _validate_function_arguments(func: F) -> None:
    """Validate the arguments of a function.

    Args:
        func: The function to validate.

    Raises:
        ValueError: If the function is not valid.
    """
    fullargspec = inspect.getfullargspec(func)
    invalid_types = {}
    for k, v in fullargspec.annotations.items():
        if k == "return":
            continue
        if v in _ALLOWED_TYPES:
            continue
        if _is_valid_collection_arg(v):
            continue
        invalid_types[k] = v
    if invalid_types:
        raise ValueError(
            f"Invalid argument types: {invalid_types}. CLI functions only "
            f"supports: {_ALLOWED_TYPES} types and {_ALLOWED_COLLECTIONS} "
            "collections."
        )


def _cli_wrapped_function(func: F) -> F:
    """Create a decorator to generate the CLI-wrapped function.

    Args:
        func: The function to decorate.

    Returns:
        The inner decorator.
    """
    _validate_function_arguments(func)

    options: List[Any] = []
    fullargspec = inspect.getfullargspec(func)
    if fullargspec.defaults is not None:
        defaults = [None] * (
            len(fullargspec.args) - len(fullargspec.defaults)
        ) + list(fullargspec.defaults)
    else:
        defaults = [None] * len(fullargspec.args)
    input_args_dict = (
        (
            arg_name,
            fullargspec.annotations.get(arg_name, None),
            defaults[i],
        )
        for i, arg_name in enumerate(fullargspec.args)
    )
    for arg_name, arg_type, arg_default in input_args_dict:
        arg_name = _cli_arg_name(arg_name)
        if arg_type == bool:
            options.append(
                click.option(
                    f"--{arg_name}",
                    type=click.BOOL,
                    is_flag=True,
                    default=False,
                    required=False,
                )
            )
        elif _is_valid_collection_arg(arg_type):
            member_type = arg_type.__args__[0]
            options.append(
                click.option(
                    f"--{arg_name}",
                    type=member_type,
                    default=arg_default,
                    required=False,
                    multiple=True,
                )
            )

        else:
            options.append(
                click.option(
                    f"--{arg_name}",
                    type=arg_type if arg_type else str,
                    default=arg_default,
                    required=False if arg_default is not None else True,
                )
            )
    options.append(
        click.command(
            help="Technical wrapper to pass into the `accelerate launch` command."
        )
    )

    def wrapper(function: F) -> F:
        for option in reversed(options):
            function = option(function)
        return function

    func.__doc__ = (
        f"{func.__doc__}\n\nThis is ZenML-generated " "CLI wrapper function."
    )

    return wrapper(func)


@contextmanager
def create_cli_wrapped_script(func: F) -> Iterator[str]:
    """Create a script with the CLI-wrapped function.

    Args:
        func: The function to use.

    Returns:
        The name of the script.
    """
    try:
        func_path = str(Path(inspect.getabsfile(func)).parent)
        script_name = random_str(20) + ".py"

        with open(script_name, "w") as f:
            f.write(
                _CLI_WRAPPED_SCRIPT_TEMPLATE.format(
                    func_path=func_path,
                    func_module=func.__module__,
                    func_name=func.__name__,
                )
            )
        path = Path(script_name)
        yield str(path.absolute())
    finally:
        path.unlink()
