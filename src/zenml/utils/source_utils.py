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
import importlib
import inspect
import os
import pathlib
import site
import sys
import types
from typing import Any, List, Optional, Type, Union

from zenml import __version__
from zenml.constants import APP_NAME
from zenml.logger import get_logger

logger = get_logger(__name__)


class LazyLoader(types.ModuleType):
    """Lazily loads modules."""

    def __init__(self, name: str) -> None:
        """Initializes a lazy loader."""
        self.module: Optional[types.ModuleType] = None
        super(LazyLoader, self).__init__(name)

    def load(self) -> types.ModuleType:
        """Loads a module and returns it."""
        if self.module is None:
            self.module = importlib.import_module(self.__name__)
            self.__dict__.update(self.module.__dict__)
        return self.module

    def __getattr__(self, item: str) -> Any:
        """Overrides the __getattr__ method with loading logic."""
        self.module = self.load()
        return getattr(self.module, item)

    def __dir__(self) -> List[str]:
        """Overrides the __dir__ method with loading logic."""
        self.module = self.load()
        return dir(self.module)


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
    from zenml.core.repo import Repository

    repo_path = pathlib.Path(Repository().path).resolve()
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


def get_path_from_source(source: str) -> str:
    """Get file path from a source string.

    Args:
        source: class_source e.g. this.module.Class.
    """
    # TODO [ENG-169]: Make sure this is an absolute path rather than naive split
    file_path = "/".join(source.split(".")[:-1]) + ".py"
    return file_path


def get_pin_from_source(source: str) -> Optional[str]:
    """Gets pin from source, i.e. module.path@pin, returns pin.

    Args:
        source: class_source e.g. this.module.Class[@pin].
    """
    if "@" in source:
        pin = source.split("@")[-1]
        return pin
    return "unpinned"


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
    from zenml.core.repo import Repository

    repo_path = Repository().path

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
    return mod.__path__[0]  # type: ignore[no-any-return, attr-defined]


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


def load_source_path_class(source: str) -> Type[Any]:
    """Loads a Python class from the source.

    Args:
        source: class_source e.g. this.module.Class[@sha]
    """
    if "@" in source:
        source = source.split("@")[0]
    logger.debug(
        "Unpinned step found with no git sha. Attempting to "
        "load class from current repository state."
    )
    class_ = import_class_by_path(source)
    return class_


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
