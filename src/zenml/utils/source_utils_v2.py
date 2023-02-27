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

import importlib
import inspect
import os
import site
import sys
from distutils.sysconfig import get_python_lib
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Type, Union

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
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


def load_source(source: Union[Source, str]) -> Any:
    if isinstance(source, str):
        source = Source.from_import_path(source)

    import_root = None
    if isinstance(source, CodeRepositorySource):
        import_root = _load_repository_files(source=source)
    elif isinstance(source, DistributionPackageSource):
        if source.version:
            current_package_version = _get_package_version(
                package_name=source.package_name
            )
            if current_package_version != source.version:
                logger.warning("Package version doesn't match source.")
    elif source.type in {SourceType.USER, SourceType.UNKNOWN}:
        # Unknown source might also refer to a user file, include source
        # root in python path just to be sure
        import_root = get_source_root()

    python_path_prefix = [import_root] if import_root else []
    with source_utils.prepend_python_path(python_path_prefix):
        module = importlib.import_module(source.module)
        object_ = getattr(module, source.variable)

    _SOURCE_MAPPING[id(object_)] = source
    return object_


def resolve_class(class_: Type[Any]) -> Source:
    if id(class_) in _SOURCE_MAPPING:
        return _SOURCE_MAPPING[id(class_)]

    module = sys.modules[class_.__module__]

    if not getattr(module, class_.__name__, None) is class_:
        raise RuntimeError(
            "Unable to resolve class, must be top level in module"
        )

    module_name = class_.__module__
    if module_name == "__main__":
        module_name = _resolve_module(module)

    source_type = get_source_type(module=module)

    if source_type == SourceType.USER:
        # TODO: maybe we want to check for a repo at the location of
        # the actual module file here? Different steps could be in
        # different code repos
        source_root = get_source_root()
        active_repo = Client().find_active_code_repository(path=source_root)

        if active_repo and not active_repo.has_local_changes:
            # Inside a clean code repo with all changes pushed, resolve to
            # a code repository source
            module_name = _resolve_module(module, root=active_repo.root)

            return CodeRepositorySource(
                repository_id=active_repo.id,
                commit=active_repo.current_commit,
                module=module_name,
                variable=class_.__name__,
            )
        else:
            module_name = _resolve_module(module)
    elif source_type == SourceType.DISTRIBUTION_PACKAGE:
        package_name = module_name.split(".", maxsplit=1)[0]
        package_version = _get_package_version(package_name=package_name)
        return DistributionPackageSource(
            module=module_name,
            variable=class_.__name__,
            version=package_version,
            type=source_type,
        )

    return Source(
        module=module_name, variable=class_.__name__, type=source_type
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


def _load_repository_files(source: CodeRepositorySource) -> str:
    source_root = get_source_root()
    active_repo = Client().find_active_code_repository(path=source_root)
    local_repo = active_repo.get_local_repo(path=source_root)
    assert local_repo

    if (
        active_repo
        and active_repo.id == source.repository_id
        and not local_repo.is_dirty
        and local_repo.current_commit == source.commit
    ):
        # The repo is clean and at the correct commit, we can use the file
        # directly without downloading anything
        repo_root = local_repo.root
    else:
        repo_root = os.path.join(
            GlobalConfiguration().config_directory,
            "code_repositories",
            str(source.repository_id),
            source.commit,
        )
        if not os.path.exists(repo_root):
            from zenml.code_repositories import BaseCodeRepository

            model = Client().get_code_repository(source.repository_id)
            repo = BaseCodeRepository.from_model(model)

            repo.download_files(commit=source.commit, directory=repo_root)

    return repo_root


def _resolve_module(
    module: ModuleType, custom_source_root: Optional[str] = None
) -> str:
    if not hasattr(module, "__file__") or not module.__file__:
        if module.__name__ == "__main__":
            raise RuntimeError(
                f"{module} module was not loaded from a file. Cannot "
                "determine the module root path."
            )
        return module.__name__

    module_path = os.path.abspath(module.__file__)

    root = custom_source_root or get_source_root()
    root = os.path.abspath(root)

    # Remove root_path from module_path to get relative path left over
    module_path = os.path.relpath(module_path, root)

    if module_path.startswith(os.pardir):
        raise RuntimeError(
            f"Unable to resolve source for module {module}. The module file "
            f"'{module_path}' does not seem to be inside the source root "
            f"'{root}'."
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


def _get_package_version(package_name: str) -> Optional[str]:
    # TODO: this only works on python 3.8+
    # TODO: catch errors
    from importlib.metadata import version

    return version(distribution_name=package_name)


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
    obj = load_source(source)

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
        obj = load_source(source)
    except Exception:
        return False

    if isinstance(obj, type) and issubclass(obj, expected_class):
        return True
    else:
        return False
