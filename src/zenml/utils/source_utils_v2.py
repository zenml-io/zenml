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

import contextlib
import importlib
import inspect
import os
import site
import sys
from distutils.sysconfig import get_python_lib
from pathlib import Path, PurePath
from types import FunctionType, ModuleType
from typing import Any, Dict, Iterator, Optional, Type, Union

from zenml.config.source import (
    CodeRepositorySource,
    DistributionPackageSource,
    Source,
    SourceType,
)
from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


_SOURCE_MAPPING: Dict[int, Source] = {}


def load(source: Union[Source, str]) -> Any:
    if isinstance(source, str):
        source = Source.from_import_path(source)

    import_root = None
    if isinstance(source, CodeRepositorySource):
        _check_local_code_repository(source=source)
        import_root = get_source_root()
    elif isinstance(source, DistributionPackageSource):
        if source.version:
            current_package_version = _get_package_version(
                package_name=source.package_name
            )
            if current_package_version != source.version:
                logger.warning(
                    "The currently installed version `%s` of package `%s` "
                    "does not match the source version `%s`. This might lead "
                    "to unexpected behavior when using the source object `%s`.",
                    current_package_version,
                    source.package_name,
                    source.version,
                    source.import_path,
                )
    elif source.type in {SourceType.USER, SourceType.UNKNOWN}:
        # Unknown source might also refer to a user file, include source
        # root in python path just to be sure
        import_root = get_source_root()

    module = _load_module(module_name=source.module, import_root=import_root)

    if source.attribute:
        obj = getattr(module, source.attribute)
    else:
        obj = module

    _SOURCE_MAPPING[id(obj)] = source
    return obj


def resolve(obj: Union[Type[Any], FunctionType, ModuleType]) -> Source:
    if id(obj) in _SOURCE_MAPPING:
        return _SOURCE_MAPPING[id(obj)]

    module = sys.modules[obj.__module__]
    attribute_name = None if isinstance(obj, ModuleType) else obj.__name__

    if attribute_name and not getattr(module, attribute_name, None) is obj:
        raise RuntimeError(
            f"Unable to resolve object `{obj}`. For the resolving to work, the "
            "class or function must be defined as top-level code (= it must "
            "get defined when importing the module) and not inside a function/"
            f"if-condition. Please make sure that your `{module.__name__}` "
            f"module has a top-level attribute `{attribute_name}` that "
            "holds the object you want to resolve."
        )

    module_name = module.__name__
    if module_name == "__main__":
        module_name = _resolve_module(module)

    source_type = get_source_type(module=module)

    if source_type == SourceType.USER:
        from zenml.client import Client

        local_repo = Client().find_active_code_repository()

        if local_repo and not local_repo.has_local_changes:
            module_name = _resolve_module(module)

            source_root = get_source_root()
            subdir = PurePath(source_root).relative_to(local_repo.root)

            return CodeRepositorySource(
                repository_id=local_repo.zenml_code_repository.id,
                commit=local_repo.current_commit,
                subdirectory=subdir.as_posix(),
                module=module_name,
                attribute=attribute_name,
            )

        module_name = _resolve_module(module)
    elif source_type == SourceType.DISTRIBUTION_PACKAGE:
        package_name = module_name.split(".", maxsplit=1)[0]
        package_version = _get_package_version(package_name=package_name)
        return DistributionPackageSource(
            module=module_name,
            attribute=attribute_name,
            version=package_version,
            type=source_type,
        )

    return Source(
        module=module_name, attribute=attribute_name, type=source_type
    )


def get_source_root() -> str:
    return source_utils.get_source_root_path()


def is_user_file(file_path: str) -> bool:
    source_root = get_source_root()
    return Path(source_root) in Path(file_path).resolve().parents


def is_standard_lib_file(file_path: str) -> bool:
    stdlib_root = get_python_lib(standard_lib=True)
    return Path(stdlib_root).resolve() in Path(file_path).resolve().parents


def is_distribution_package_file(file_path: str) -> bool:
    absolute_file_path = Path(file_path).resolve()

    for path in site.getsitepackages() + [site.getusersitepackages()]:
        if Path(path).resolve() in absolute_file_path.parents:
            return True

    # TODO: This currently returns False for editable installs because
    # the site packages dir only contains a reference to the source files,
    # not the actual files. This means editable installs will get source
    # type unknown, which seems reasonable but we need to check if this
    # leads to some issues
    return False


def get_source_type(module: ModuleType) -> SourceType:
    try:
        file_path = inspect.getfile(module)
    except (TypeError, OSError):
        # builtin file
        return SourceType.BUILTIN

    if is_standard_lib_file(file_path=file_path):
        return SourceType.BUILTIN

    if is_user_file(file_path=file_path):
        return SourceType.USER

    if is_distribution_package_file(file_path=file_path):
        return SourceType.DISTRIBUTION_PACKAGE

    return SourceType.UNKNOWN


@contextlib.contextmanager
def prepend_python_path(path: str) -> Iterator[None]:
    """Context manager to temporarily prepend a path to the python path.

    Args:
        path: Path that will be prepended to sys.path for the duration of
            the context manager.

    Yields:
        None
    """
    try:
        sys.path.insert(0, path)
        yield
    finally:
        sys.path.remove(path)


def _check_local_code_repository(source: CodeRepositorySource) -> None:
    from zenml.client import Client

    local_repo = Client().find_active_code_repository()

    if (
        not local_repo
        or local_repo.zenml_code_repository.id != source.repository_id
    ):
        logger.warning("No or wrong code repo for source")
    elif local_repo.current_commit != source.commit:
        logger.warning("Wrong commit")
    elif local_repo.is_dirty:
        logger.warning("Repo dirty")


def _resolve_module(
    module: ModuleType, custom_source_root: Optional[str] = None
) -> str:
    if not hasattr(module, "__file__") or not module.__file__:
        if module.__name__ == "__main__":
            raise RuntimeError(
                f"Unable to resolve module `{module}` because it was "
                "not loaded from a file."
            )
        return module.__name__

    module_file = os.path.abspath(module.__file__)

    source_root = custom_source_root or get_source_root()
    source_root = os.path.abspath(source_root)

    module_source_path = os.path.relpath(module_file, source_root)

    if module_source_path.startswith(os.pardir):
        raise RuntimeError(
            f"Unable to resolve module `{module}`. The file from which the "
            f"module was loaded ({module_file}) is outside the source root "
            f"({source_root})."
        )

    # Remove the file extension and replace the os specific path separators
    # with `.` to get the module source
    module_source_path, file_extension = os.path.splitext(module_source_path)
    if file_extension != ".py":
        raise RuntimeError(
            f"Unable to resolve module `{module}`. The file from which the "
            f"module was loaded ({module_file}) is not a python file."
        )

    module_source = module_source_path.replace(os.path.sep, ".")

    logger.debug("Resolved module `%s` to `%s`", module, module_source)

    return module_source


def _load_module(
    module_name: str, import_root: Optional[str] = None
) -> ModuleType:
    if import_root:
        with prepend_python_path(import_root):
            return importlib.import_module(module_name)
    else:
        return importlib.import_module(module_name)


def _get_package_version(package_name: str) -> Optional[str]:
    # TODO: this only works on python 3.8+
    # TODO: catch errors
    from importlib.metadata import version

    try:
        return version(distribution_name=package_name)
    except:
        return None


# Ideally both the expected_class and return type should be annotated with a
# type var to indicate that both they represent the same type. However, mypy
# currently doesn't support this for abstract classes:
# https://github.com/python/mypy/issues/4717
def load_and_validate_class(
    source: Union[str, Source], expected_class: Type[Any]
) -> Type[Any]:
    """Loads a source class and validates its type.

    Args:
        source: The source.
        expected_class: The class that the source should resolve to.

    Raises:
        TypeError: If the source does not resolve to the expected type.

    Returns:
        The resolved source class.
    """
    obj = load(source)

    if isinstance(obj, type) and issubclass(obj, expected_class):
        return obj
    else:
        raise TypeError(
            f"Error while loading `{source}`. Expected class "
            f"{expected_class.__name__}, got {obj} instead."
        )


def validate_source_class(
    source: Union[Source, str], expected_class: Type[Any]
) -> bool:
    """Validates that a source resolves to a certain type.

    Args:
        source: The source to validate.
        expected_class: The class that the source should resolve to.

    Returns:
        If the source resolves to the expected class.
    """
    try:
        obj = load(source)
    except Exception:
        return False

    if isinstance(obj, type) and issubclass(obj, expected_class):
        return True
    else:
        return False
