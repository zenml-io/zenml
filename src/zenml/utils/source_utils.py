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
"""Utility functions for source code.

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
from distutils.sysconfig import get_python_lib
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import Any, Callable, Iterator, List, Optional, Type, Union

from zenml import __version__
from zenml.constants import APP_NAME
from zenml.enums import StackComponentType
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.stack import StackComponent

logger = get_logger(__name__)


def is_standard_pin(pin: str) -> bool:
    """Returns `True` if pin is valid ZenML pin, else False.

    Args:
        pin: potential ZenML pin like 'zenml_0.1.1'

    Returns:
        `True` if pin is valid ZenML pin, else False.
    """
    if pin.startswith(f"{APP_NAME}_"):
        return True
    return False


def is_inside_repository(file_path: str) -> bool:
    """Returns whether a file is inside a zenml repository.

    Args:
        file_path: A file path.

    Returns:
        `True` if the file is inside a zenml repository, else `False`.
    """
    from zenml.repository import Repository

    repo_path = Repository.find_repository()
    if not repo_path:
        return False

    repo_path = repo_path.resolve()
    absolute_file_path = pathlib.Path(file_path).resolve()
    return repo_path in absolute_file_path.parents


def is_third_party_module(file_path: str) -> bool:
    """Returns whether a file belongs to a third party package.

    Args:
        file_path: A file path.

    Returns:
        `True` if the file belongs to a third party package, else `False`.
    """
    absolute_file_path = pathlib.Path(file_path).resolve()

    for path in site.getsitepackages() + [
        site.getusersitepackages(),
        get_python_lib(standard_lib=True),
    ]:
        if pathlib.Path(path).resolve() in absolute_file_path.parents:
            return True

    return False


def create_zenml_pin() -> str:
    """Creates a ZenML pin for source pinning from release version.

    Returns:
        ZenML pin.
    """
    return f"{APP_NAME}_{__version__}"


def resolve_standard_source(source: str) -> str:
    """Creates a ZenML pin for source pinning from release version.

    Args:
        source: class_source e.g. this.module.Class.

    Returns:
        ZenML pin.

    Raises:
        AssertionError: If source is already pinned.
    """
    if "@" in source:
        raise AssertionError(f"source {source} is already pinned.")
    pin = create_zenml_pin()
    return f"{source}@{pin}"


def is_standard_source(source: str) -> bool:
    """Returns `True` if source is a standard ZenML source.

    Args:
        source: class_source e.g. this.module.Class[@pin].

    Returns:
        `True` if source is a standard ZenML source, else `False`.
    """
    if source.split(".")[0] == "zenml":
        return True
    return False


def get_class_source_from_source(source: str) -> str:
    """Gets class source from source, i.e. module.path@version, returns version.

    Args:
        source: source pointing to potentially pinned sha.

    Returns:
        class_source e.g. this.module.Class.
    """
    # source need not even be pinned
    return source.split("@")[0]


def get_module_source_from_source(source: str) -> str:
    """Gets module source from source.

    For example `some.module.file.class@version` would
    return `some.module`.

    Args:
        source: source pointing to potentially pinned sha.

    Returns:
        module_source e.g. some.module.
    """
    class_source = get_class_source_from_source(source)
    return ".".join(class_source.split(".")[:-2])


def get_module_source_from_module(module: ModuleType) -> str:
    """Gets the source of the supplied module.

    E.g.:

      * a `/home/myrepo/src/run.py` module running as the main module returns
      `run` if no repository root is specified.

      * a `/home/myrepo/src/run.py` module running as the main module returns
      `src.run` if the repository root is configured in `/home/myrepo`

      * a `/home/myrepo/src/pipeline.py` module not running as the main module
      returns `src.pipeline` if the repository root is configured in
      `/home/myrepo`

      * a `/home/myrepo/src/pipeline.py` module not running as the main module
      returns `pipeline` if no repository root is specified and the main
      module is also in `/home/myrepo/src`.

      * a `/home/step.py` module not running as the main module
      returns `step` if the CWD is /home and the repository root or the main
      module are in a different path (e.g. `/home/myrepo/src`).

    Args:
        module: the module to get the source of.

    Returns:
        The source of the main module.

    Raises:
        RuntimeError: if the module is not loaded from a file
    """
    if not hasattr(module, "__file__") or not module.__file__:
        if module.__name__ == "__main__":
            raise RuntimeError(
                f"{module} module was not loaded from a file. Cannot "
                "determine the module root path."
            )
        return module.__name__
    module_path = os.path.abspath(module.__file__)

    root_path = get_source_root_path()

    if not module_path.startswith(root_path):
        root_path = os.getcwd()
        logger.warning(
            "User module %s is not in the source root. Using current "
            "directory %s instead to resolve module source.",
            module,
            root_path,
        )

    root_path = os.path.abspath(root_path)

    # Remove root_path from module_path to get relative path left over
    module_path = os.path.relpath(module_path, root_path)

    if module_path.startswith(os.pardir):
        raise RuntimeError(
            f"Unable to resolve source for module {module}. The module file "
            f"'{module_path}' does not seem to be inside the source root "
            f"'{root_path}'."
        )

    # Remove the file extension and replace the os specific path separators
    # with `.` to get the module source
    module_path, file_extension = os.path.splitext(module_path)
    if file_extension != ".py":
        raise RuntimeError(
            f"Unable to resolve source for module {module}. The module file "
            f"'{module_path}' does not seem to be a python file."
        )

    module_source = module_path.replace(os.path.sep, ".")

    logger.debug(
        f"Resolved module source for module {module} to: `{module_source}`"
    )

    return module_source


def get_relative_path_from_module_source(module_source: str) -> str:
    """Get a directory path from module, relative to root of the package tree.

    E.g. zenml.core.step will return zenml/core/step.

    Args:
        module_source: A module e.g. zenml.core.step

    Returns:
        A relative path e.g. zenml/core/step.
    """
    return module_source.replace(".", os.path.sep)


def get_absolute_path_from_module_source(module: str) -> str:
    """Get a directory path from module source.

    E.g. `zenml.core.step` will return `full/path/to/zenml/core/step`.

    Args:
        module: A module e.g. `zenml.core.step`.

    Returns:
        An absolute path e.g. `full/path/to/zenml/core/step`.
    """
    mod = importlib.import_module(module)
    return mod.__path__[0]


def get_source_root_path() -> str:
    """Gets repository root path or the source root path of the current process.

    E.g.:

      * if the process was started by running a `run.py` file under
      `full/path/to/my/run.py`, and the repository root is configured at
      `full/path`, the source root path is `full/path`.

      * same case as above, but when there is no repository root configured,
      the source root path is `full/path/to/my`.

    Returns:
        The source root path of the current process.

    Raises:
        RuntimeError: if the main module was not started or determined.
    """
    from zenml.repository import Repository

    repo_root = Repository.find_repository()
    if repo_root:
        logger.debug("Using repository root as source root: %s", repo_root)
        return str(repo_root.resolve())

    main_module = sys.modules.get("__main__")
    if main_module is None:
        raise RuntimeError(
            "Could not determine the main module used to run the current "
            "process."
        )

    if not hasattr(main_module, "__file__") or not main_module.__file__:
        raise RuntimeError(
            "Main module was not started from a file. Cannot "
            "determine the module root path."
        )
    path = pathlib.Path(main_module.__file__).resolve().parent

    logger.debug("Using main module location as source root: %s", path)
    return str(path)


def get_module_source_from_class(
    class_: Union[Type[Any], str]
) -> Optional[str]:
    """Takes class input and returns module_source.

    If class is already string then returns the same.

    Args:
        class_: object of type class.

    Returns:
        module_source of class.

    Raises:
        AssertionError: if step_type is neither a class nor a string.
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
    else:
        # Use standard inspect if running outside a notebook
        src = inspect.getsource(value)
    return src


def get_hashed_source(value: Any) -> str:
    """Returns a hash of the objects source code.

    Args:
        value: object to get source from.

    Returns:
        Hash of source code.

    Raises:
        TypeError: If unable to compute the hash.
    """
    try:
        source_code = get_source(value)
    except TypeError:
        raise TypeError(
            f"Unable to compute the hash of source code of object: {value}."
        )
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()


def resolve_class(class_: Type[Any]) -> str:
    """Resolves a class into a serializable source string.

    For classes that are not built-in nor imported from a Python package, the
    `get_source_root_path` function is used to determine the root path
    relative to which the class source is resolved.

    Args:
        class_: A Python Class reference.

    Returns:
        source_path e.g. this.module.Class.
    """
    initial_source = class_.__module__ + "." + class_.__name__
    if is_standard_source(initial_source):
        return resolve_standard_source(initial_source)

    try:
        file_path = inspect.getfile(class_)
    except TypeError:
        # builtin file
        return initial_source

    if initial_source.startswith("__main__") or is_third_party_module(
        file_path
    ):
        return initial_source

    # Regular user file -> get the full module path relative to the
    # source root.
    module_source = get_module_source_from_module(
        sys.modules[class_.__module__]
    )

    source = module_source + "." + class_.__name__
    logger.debug(f"Resolved class {class_} to `{source}`.")
    return source


def import_class_by_path(class_path: str) -> Type[Any]:
    """Imports a class based on a given path.

    Args:
        class_path: str, class_source e.g. this.module.Class

    Returns:
        the given class
    """
    modulename, classname = class_path.rsplit(".", 1)
    mod = importlib.import_module(modulename)
    return getattr(mod, classname)  # type: ignore[no-any-return]


@contextmanager
def prepend_python_path(paths: List[str]) -> Iterator[None]:
    """Simple context manager to help import module within the repo.

    Args:
        paths: paths to prepend to sys.path

    Yields:
        None
    """
    try:
        # Entering the with statement
        for path in paths:
            sys.path.insert(0, path)
        yield
    finally:
        # Exiting the with statement
        for path in paths:
            sys.path.remove(path)


def load_source_path_class(
    source: str, import_path: Optional[str] = None
) -> Type[Any]:
    """Loads a Python class from the source.

    Args:
        source: class_source e.g. this.module.Class[@sha]
        import_path: optional path to add to python path

    Returns:
        the given class
    """
    from zenml.repository import Repository

    repo_root = Repository.find_repository()
    if not import_path and repo_root:
        import_path = str(repo_root)

    if "@" in source:
        source = source.split("@")[0]

    if import_path is not None:
        with prepend_python_path([import_path]):
            logger.debug(
                f"Loading class {source} with import path {import_path}"
            )
            return import_class_by_path(source)
    return import_class_by_path(source)


def import_python_file(file_path: str, zen_root: str) -> types.ModuleType:
    """Imports a python file in relationship to the zen root.

    Args:
        file_path: Path to python file that should be imported.
        zen_root: Path to current zenml root

    Returns:
        imported module: Module
    """
    file_path = os.path.abspath(file_path)
    module_path = os.path.relpath(file_path, zen_root)
    module_name = os.path.splitext(module_path)[0].replace(os.path.sep, ".")

    if module_name in sys.modules:
        del sys.modules[module_name]
        # Add directory of python file to PYTHONPATH so we can import it
        with prepend_python_path([zen_root]):
            module = importlib.import_module(module_name)
        return module
    else:
        # Add directory of python file to PYTHONPATH so we can import it
        with prepend_python_path([zen_root]):
            module = importlib.import_module(module_name)
        return module


def validate_flavor_source(
    source: str, component_type: StackComponentType
) -> Type[StackComponent]:
    """Import a StackComponent class from a given source and validate its type.

    Args:
        source: source path of the implementation
        component_type: the type of the stack component

    Returns:
        the imported class

    Raises:
        ValueError: If ZenML cannot find the given module path
        TypeError: If the given module path does not point to a subclass of a
            StackComponent which has the right component type.
    """
    try:
        stack_component_class = load_source_path_class(source)
    except (ValueError, AttributeError, ImportError) as e:
        raise ValueError(
            f"ZenML can not import the flavor class '{source}': {e}"
        )

    if not issubclass(stack_component_class, StackComponent):
        raise TypeError(
            f"The source '{source}' does not point to a subclass of the ZenML"
            f"StackComponent."
        )

    if stack_component_class.TYPE != component_type:  # noqa
        raise TypeError(
            f"The source points to a {stack_component_class.TYPE}, not a "  # noqa
            f"{component_type}."
        )

    return stack_component_class  # noqa
