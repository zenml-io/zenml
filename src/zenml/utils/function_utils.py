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
from typing import Any, Callable, Iterator, List, TypeVar, Union

import click

from zenml.utils.string_utils import random_str

F = TypeVar("F", bound=Callable[..., None])

_CLI_WRAPPED_SCRIPT_TEMPLATE_HEADER = """
from zenml.utils.function_utils import _cli_wrapped_function

import sys
sys.path.append("{func_path}")
from {func_module} import {func_name} as func_to_wrap

if entrypoint:=getattr(func_to_wrap, "entrypoint", None):
    func = _cli_wrapped_function(entrypoint)
else:
    func = _cli_wrapped_function(func_to_wrap)

"""
_CLI_WRAPPED_ACCELERATE_MAIN = """
if __name__=="__main__":
    from accelerate import Accelerator
    import cloudpickle as pickle
    accelerator = Accelerator()
    ret = func()
    if accelerator.is_main_process:
        pickle.dump(ret, open("{output_file}", "wb"))
"""
_ALLOWED_TYPES = (str, int, float, bool, Path)
_ALLOWED_COLLECTIONS = (tuple,)
__TYPES_MAPPER = {
    str: click.STRING,
    int: click.INT,
    float: click.FLOAT,
    bool: click.BOOL,
    Path: click.STRING,
    None: click.STRING,
}


def _cli_arg_name(arg_name: str) -> str:
    return arg_name.replace("_", "-")


def _is_valid_collection_arg(arg_type: Any) -> bool:
    if getattr(arg_type, "__origin__", None) in _ALLOWED_COLLECTIONS:
        if arg_type.__args__[0] not in _ALLOWED_TYPES:
            return False
        return True
    return False


def _is_valid_optional_arg(arg_type: Any) -> bool:
    if (
        getattr(arg_type, "_name", None) == "Optional"
        and getattr(arg_type, "__origin__", None) == Union
    ):
        if args := getattr(arg_type, "__args__", None):
            if len(args) != 2:
                return False
            if (
                args[0] not in _ALLOWED_TYPES
                and not _is_valid_collection_arg(args[0])
            ) or args[1] != type(None):
                return False
        return True
    return False


def _cli_wrapped_function(func: F) -> F:
    """Create a decorator to generate the CLI-wrapped function.

    Args:
        func: The function to decorate.

    Returns:
        The inner decorator.

    Raises:
        ValueError: If the function arguments are not valid.
    """
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
    invalid_types = {}
    for arg_name, arg_type, arg_default in input_args_dict:
        if _is_valid_optional_arg(arg_type):
            arg_type = arg_type.__args__[0]
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
        elif arg_type in _ALLOWED_TYPES:
            options.append(
                click.option(
                    f"--{arg_name}",
                    type=__TYPES_MAPPER[arg_type],
                    default=arg_default,
                    required=False if arg_default is not None else True,
                )
            )
        else:
            invalid_types[arg_name] = arg_type
    if invalid_types:
        raise ValueError(
            f"Invalid argument types: {invalid_types}. CLI functions only "
            f"supports: {_ALLOWED_TYPES} types (including Optional) and "
            f"{_ALLOWED_COLLECTIONS} collections."
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
def create_cli_wrapped_script(
    func: F, flavour: str = "accelerate"
) -> Iterator[str]:
    """Create a script with the CLI-wrapped function.

    Args:
        func: The function to use.
        flavour: The flavour to use.

    Returns:
        The name of the script and the name of the output.
    """
    try:
        func_path = str(Path(inspect.getabsfile(func)).parent)
        random_name = random_str(20)
        script_name = random_name + ".py"
        output_name = random_name + ".out"

        with open(script_name, "w") as f:
            f.write(
                _CLI_WRAPPED_SCRIPT_TEMPLATE_HEADER.format(
                    func_path=func_path,
                    func_module=func.__module__,
                    func_name=func.__name__,
                )
            )
            if flavour == "accelerate":
                f.write(
                    _CLI_WRAPPED_ACCELERATE_MAIN.format(
                        output_file=output_name
                    )
                )
        path = Path(script_name)
        output_path = Path(output_name)
        yield str(path.absolute()), str(output_path.absolute())
    finally:
        pass
        # path.unlink()
        # output_path.unlink()
