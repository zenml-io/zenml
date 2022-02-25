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
"""
These utils are predicated on the following definitions:

* class_source: This is a python-import type path to a class, e.g.
    some.mod.class
* module_source: This is a python-import type path to a module, e.g. some.mod
* file_path, relative_path, absolute_path: These are file system paths.
* source: This is a class_source or module_source. If it is a class_source, it
    can also be optionally pinned.
* pin: Whatever comes after the `@` symbol from a source, usually the git sha
    or the version of zenml as a string.
"""
import hashlib
import importlib
import inspect
import os
import pathlib
import site
import sys
import types
from contextlib import contextmanager
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import Any, Callable, Iterator, Optional, Type, Union

from zenml import __version__
from zenml.constants import APP_NAME
from zenml.environment import Environment
from zenml.logger import get_logger

logger = get_logger(__name__)


def is_standard_pin(pin: str) -> bool:
    """Returns `True` if pin is valid ZenML pin, else False.

    Args:
        pin: potential ZenML pin like 'zenml_0.1.1'
    """
    if pin.startswith(f"{APP_NAME}_"):
        return True
    return False


def is_inside_repository(file_path: str) -> bool:
    """Returns whether a file is inside a zenml repository."""
    from zenml.repository import Repository

    repo_path = Repository.find_repository().resolve()
    absolute_file_path = pathlib.Path(file_path).resolve()
    return repo_path in absolute_file_path.parents


def is_third_party_module(file_path: str) -> bool:
    """Returns whether a file belongs to a third party package."""
    absolute_file_path = pathlib.Path(file_path).resolve()

    for path in site.getsitepackages() + [site.getusersitepackages()]:
        if pathlib.Path(path).resolve() in absolute_file_path.parents:
            return True

    return False


def create_zenml_pin() -> str:
    """Creates a ZenML pin for source pinning from release version."""
    return f"{APP_NAME}_{__version__}"


def resolve_standard_source(source: str) -> str:
    """Creates a ZenML pin for source pinning from release version.

    Args:
        source: class_source e.g. this.module.Class.
    """
    if "@" in source:
        raise AssertionError(f"source {source} is already pinned.")
    pin = create_zenml_pin()
    return f"{source}@{pin}"


def is_standard_source(source: str) -> bool:
    """Returns `True` if source is a standard ZenML source.

    Args:
        source: class_source e.g. this.module.Class[@pin].
    """
    if source.split(".")[0] == "zenml":
        return True
    return False


def get_class_source_from_source(source: str) -> str:
    """Gets class source from source, i.e. module.path@version, returns version.

    Args:
        source: source pointing to potentially pinned sha.
    """
    # source need not even be pinned
    return source.split("@")[0]


def get_module_source_from_source(source: str) -> str:
    """Gets module source from source. E.g. `some.module.file.class@version`,
    returns `some.module`.

    Args:
        source: source pointing to potentially pinned sha.
    """
    class_source = get_class_source_from_source(source)
    return ".".join(class_source.split(".")[:-2])


def get_module_source_from_file_path(file_path: str) -> str:
    """Gets module_source from a file_path. E.g. `/home/myrepo/step/trainer.py`
    returns `myrepo.step.trainer` if `myrepo` is the root of the repo.

    Args:
        file_path: Absolute file path to a file within the module.
    """
    from zenml.repository import Repository

    repo_path = str(Repository.find_repository().resolve())

    # Replace repo_path with file_path to get relative path left over
    relative_file_path = file_path.replace(repo_path, "")[1:]

    # Kick out the .py and replace `/` with `.` to get the module source
    relative_file_path = relative_file_path.replace(".py", "")
    module_source = relative_file_path.replace("/", ".")
    return module_source


def get_relative_path_from_module_source(module_source: str) -> str:
    """Get a directory path from module, relative to root of repository.

    E.g. zenml.core.step will return zenml/core/step.

    Args:
        module_source: A module e.g. zenml.core.step
    """
    return module_source.replace(".", "/")


def get_absolute_path_from_module_source(module: str) -> str:
    """Get a directory path from module source.

    E.g. `zenml.core.step` will return `full/path/to/zenml/core/step`.

    Args:
        module: A module e.g. `zenml.core.step`.
    """
    mod = importlib.import_module(module)
    return mod.__path__[0]


def get_module_source_from_class(
    class_: Union[Type[Any], str]
) -> Optional[str]:
    """Takes class input and returns module_source. If class is already string
    then returns the same.

    Args:
        class_: object of type class.
    """
    if isinstance(class_, str):
        module_source = class_
    else:
        # Infer it from the class provided
        if not inspect.isclass(class_):
            raise AssertionError("step_type is neither string nor class.")
        module_source = class_.__module__ + "." + class_.__name__
    return module_source


def get_source(value: Any) -> str:
    """Returns the source code of an object. If executing within a IPython
    kernel environment, then this monkey-patches `inspect` module temporarily
    with a workaround to get source from the cell.

    Raises:
        TypeError: If source not found.
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
            for name, member in inspect.getmembers(object):
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
        inspect.getfile = _old_getfile
    else:
        # Use standard inspect if running outside a notebook
        src = inspect.getsource(value)
    return src


def get_hashed_source(value: Any) -> str:
    """Returns a hash of the objects source code."""
    try:
        source_code = get_source(value)
    except TypeError:
        raise TypeError(
            f"Unable to compute the hash of source code of object: {object}."
        )
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()


def resolve_class(class_: Type[Any]) -> str:
    """Resolves a class into a serializable source string.

    Args:
        class_: A Python Class reference.

    Returns: source_path e.g. this.module.Class.
    """
    initial_source = class_.__module__ + "." + class_.__name__
    if is_standard_source(initial_source):
        return resolve_standard_source(initial_source)

    try:
        file_path = inspect.getfile(class_)
    except TypeError:
        # builtin file
        return initial_source

    if (
        initial_source.startswith("__main__")
        or not is_inside_repository(file_path)
        or is_third_party_module(file_path)
    ):
        return initial_source

    # Regular user file inside the repository -> get the full module
    # path relative to the repository
    module_source = get_module_source_from_file_path(file_path)

    # ENG-123 Sanitize for Windows OS
    # module_source = module_source.replace("\\", ".")

    return module_source + "." + class_.__name__


def import_class_by_path(class_path: str) -> Type[Any]:
    """Imports a class based on a given path

    Args:
        class_path: str, class_source e.g. this.module.Class

    Returns: the given class
    """
    classname = class_path.split(".")[-1]
    modulename = ".".join(class_path.split(".")[0:-1])
    mod = importlib.import_module(modulename)
    return getattr(mod, classname)  # type: ignore[no-any-return]


@contextmanager
def prepend_python_path(path: str) -> Iterator[None]:
    """Simple context manager to help import module within the repo"""
    try:
        # Entering the with statement
        sys.path.insert(0, path)
        yield
    finally:
        # Exiting the with statement
        sys.path.remove(path)


def load_source_path_class(source: str) -> Type[Any]:
    """Loads a Python class from the source.

    Args:
        source: class_source e.g. this.module.Class[@sha]
    """
    from zenml.repository import Repository

    repo_path = str(Repository.find_repository())

    if "@" in source:
        source = source.split("@")[0]
    else:
        logger.debug(
            "Unpinned source path found with no git sha: %s. Attempting to "
            "load class from current repository state.",
            source,
        )

    with prepend_python_path(repo_path):
        return import_class_by_path(source)


def import_python_file(file_path: str) -> types.ModuleType:
    """Imports a python file.

    Args:
        file_path: Path to python file that should be imported.

    Returns:
        The imported module.
    """
    # Add directory of python file to PYTHONPATH so we can import it
    file_path = os.path.abspath(file_path)
    sys.path.append(os.path.dirname(file_path))

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    return importlib.import_module(module_name)
