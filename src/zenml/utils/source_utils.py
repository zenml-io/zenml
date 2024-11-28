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
"""Utilities for loading/resolving objects."""

import contextlib
import importlib
import inspect
import os
import site
import sys
from distutils.sysconfig import get_python_lib
from pathlib import Path, PurePath
from types import BuiltinFunctionType, FunctionType, ModuleType
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    Optional,
    Type,
    Union,
    cast,
)
from uuid import UUID

from zenml.config.source import (
    CodeRepositorySource,
    DistributionPackageSource,
    NotebookSource,
    Source,
    SourceType,
)
from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.utils import notebook_utils

logger = get_logger(__name__)

ZENML_SOURCE_ATTRIBUTE_NAME = "__zenml_source__"

NoneType = type(None)
NoneTypeSource = Source(
    module=NoneType.__module__, attribute="NoneType", type=SourceType.BUILTIN
)
FunctionTypeSource = Source(
    module=FunctionType.__module__,
    attribute=FunctionType.__name__,
    type=SourceType.BUILTIN,
)
BuiltinFunctionTypeSource = Source(
    module=BuiltinFunctionType.__module__,
    attribute=BuiltinFunctionType.__name__,
    type=SourceType.BUILTIN,
)


_CUSTOM_SOURCE_ROOT: Optional[str] = os.getenv(
    ENV_ZENML_CUSTOM_SOURCE_ROOT, None
)

_SHARED_TEMPDIR: Optional[str] = None
_resolved_notebook_sources: Dict[str, str] = {}
_notebook_modules: Dict[str, UUID] = {}


def load(source: Union[Source, str]) -> Any:
    """Load a source or import path.

    Args:
        source: The source to load.

    Returns:
        The loaded object.
    """
    if isinstance(source, str):
        source = Source.from_import_path(source)

    # The types of some objects don't exist in the `builtin` module
    # so we need to manually handle it here
    if source.import_path == NoneTypeSource.import_path:
        return NoneType
    elif source.import_path == FunctionTypeSource.import_path:
        return FunctionType
    elif source.import_path == BuiltinFunctionTypeSource.import_path:
        return BuiltinFunctionType

    import_root = None
    if source.type == SourceType.CODE_REPOSITORY:
        source = CodeRepositorySource.model_validate(dict(source))
        _warn_about_potential_source_loading_issues(source=source)
        import_root = get_source_root()
    elif source.type == SourceType.DISTRIBUTION_PACKAGE:
        source = DistributionPackageSource.model_validate(dict(source))
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
    elif source.type == SourceType.NOTEBOOK:
        if Environment.in_notebook():
            # If we're in a notebook, we don't need to do anything as the
            # loading from the __main__ module should work just fine.
            pass
        else:
            notebook_source = NotebookSource.model_validate(dict(source))
            return _try_to_load_notebook_source(notebook_source)
    elif source.type in {SourceType.USER, SourceType.UNKNOWN}:
        # Unknown source might also refer to a user file, include source
        # root in python path just to be sure
        import_root = get_source_root()

    if _should_load_from_main_module(source):
        # This source points to the __main__ module of the current process.
        # If we were to load the module here, we would load the same python
        # file with a different module name, which would rerun all top-level
        # code. To avoid this, we instead load the source from the __main__
        # module which is already loaded.
        module = sys.modules["__main__"]
    else:
        module = _load_module(
            module_name=source.module, import_root=import_root
        )

    if source.attribute:
        obj = getattr(module, source.attribute)
    else:
        obj = module

    return obj


def resolve(
    obj: Union[
        Type[Any],
        Callable[..., Any],
        ModuleType,
        FunctionType,
        BuiltinFunctionType,
        NoneType,
    ],
    skip_validation: bool = False,
) -> Source:
    """Resolve an object.

    Args:
        obj: The object to resolve.
        skip_validation: If True, the validation that the object exist in the
            module is skipped.

    Raises:
        RuntimeError: If the object can't be resolved.

    Returns:
        The source of the resolved object.
    """
    # The types of some objects don't exist in the `builtin` module
    # so we need to manually handle it here
    if obj is NoneType:
        return NoneTypeSource
    elif obj is FunctionType:
        return FunctionTypeSource
    elif obj is BuiltinFunctionType:
        return BuiltinFunctionTypeSource
    elif source := getattr(obj, ZENML_SOURCE_ATTRIBUTE_NAME, None):
        assert isinstance(source, Source)
        return source
    elif isinstance(obj, ModuleType):
        module = obj
        attribute_name = None
    else:
        module = sys.modules[obj.__module__]
        attribute_name = obj.__name__  # type: ignore[union-attr]

    if (
        not (skip_validation or getattr(obj, "_DOCS_BUILDING_MODE", False))
        and attribute_name
        and getattr(module, attribute_name, None) is not obj
    ):
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
        from zenml.utils import code_repository_utils

        local_repo_context = (
            code_repository_utils.find_active_code_repository()
        )

        if local_repo_context and not local_repo_context.has_local_changes:
            module_name = _resolve_module(module)

            source_root = get_source_root()
            subdir = PurePath(source_root).relative_to(local_repo_context.root)

            return CodeRepositorySource(
                repository_id=local_repo_context.code_repository_id,
                commit=local_repo_context.current_commit,
                subdirectory=subdir.as_posix(),
                module=module_name,
                attribute=attribute_name,
                type=SourceType.CODE_REPOSITORY,
            )

        module_name = _resolve_module(module)
    elif source_type == SourceType.DISTRIBUTION_PACKAGE:
        package_name = _get_package_for_module(module_name=module_name)
        if package_name:
            package_version = _get_package_version(package_name=package_name)
            return DistributionPackageSource(
                module=module_name,
                attribute=attribute_name,
                package_name=package_name,
                version=package_version,
                type=source_type,
            )
        else:
            # Fallback to an unknown source if we can't find the package
            source_type = SourceType.UNKNOWN
    elif source_type == SourceType.NOTEBOOK:
        source = NotebookSource(
            module="__main__",
            attribute=attribute_name,
            type=source_type,
        )

        if module_name in _notebook_modules:
            source.replacement_module = module_name
            source.artifact_store_id = _notebook_modules[module_name]
        elif cell_code := notebook_utils.load_notebook_cell_code(obj):
            replacement_module = (
                notebook_utils.compute_cell_replacement_module_name(
                    cell_code=cell_code
                )
            )
            source.replacement_module = replacement_module
            _resolved_notebook_sources[source.import_path] = cell_code

        return source

    return Source(
        module=module_name, attribute=attribute_name, type=source_type
    )


def get_source_root() -> str:
    """Get the source root.

    The source root will be determined in the following order:
    - The manually specified custom source root if it was set.
    - The ZenML repository directory if one exists in the current working
      directory or any parent directories.
    - The parent directory of the main module file.

    Returns:
        The source root.

    Raises:
        RuntimeError: If the main module file can't be found.
    """
    if _CUSTOM_SOURCE_ROOT:
        logger.debug("Using custom source root: %s", _CUSTOM_SOURCE_ROOT)
        return _CUSTOM_SOURCE_ROOT

    from zenml.client import Client

    repo_root = Client.find_repository()
    if repo_root:
        logger.debug("Using repository root as source root: %s", repo_root)
        return str(repo_root.resolve())

    main_module = sys.modules.get("__main__")
    if main_module is None:
        raise RuntimeError(
            "Unable to determine source root because the main module could not "
            "be found."
        )

    if not hasattr(main_module, "__file__") or not main_module.__file__:
        raise RuntimeError(
            "Unable to determine source root because the main module does not "
            "have an associated file. This could be because you're running in "
            "an interactive Python environment. If you are trying to run from "
            "within a Jupyter notebook, please run `zenml init` from the root "
            "where your notebook is located and restart your notebook server.   "
        )

    path = Path(main_module.__file__).resolve().parent

    logger.debug("Using main module parent directory as source root: %s", path)
    return str(path)


def set_custom_source_root(source_root: Optional[str]) -> None:
    """Sets a custom source root.

    If set this has the highest priority and will always be used as the source
    root.

    Args:
        source_root: The source root to use.
    """
    logger.debug("Setting custom source root: %s", source_root)
    global _CUSTOM_SOURCE_ROOT
    _CUSTOM_SOURCE_ROOT = source_root


def is_internal_module(module_name: str) -> bool:
    """Checks if a module is internal (=part of the zenml package).

    Args:
        module_name: Name of the module to check.

    Returns:
        True if the module is internal, False otherwise.
    """
    return module_name.split(".", maxsplit=1)[0] == "zenml"


def is_user_file(file_path: str) -> bool:
    """Checks if a file is a user file.

    Args:
        file_path: The file path to check.

    Returns:
        True if the file is a user file, False otherwise.
    """
    source_root = get_source_root()
    return Path(source_root) in Path(file_path).resolve().parents


def is_standard_lib_file(file_path: str) -> bool:
    """Checks if a file belongs to the Python standard library.

    Args:
        file_path: The file path to check.

    Returns:
        True if the file belongs to the Python standard library, False
        otherwise.
    """
    stdlib_root = get_python_lib(standard_lib=True)
    logger.debug("Standard library root: %s", stdlib_root)
    return Path(stdlib_root).resolve() in Path(file_path).resolve().parents


def is_distribution_package_file(file_path: str, module_name: str) -> bool:
    """Checks if a file/module belongs to a distribution package.

    Args:
        file_path: The file path to check.
        module_name: The module name.

    Returns:
        True if the file/module belongs to a distribution package, False
        otherwise.
    """
    absolute_file_path = Path(file_path).resolve()

    for path in site.getsitepackages() + [site.getusersitepackages()]:
        if Path(path).resolve() in absolute_file_path.parents:
            return True

    # TODO: The previous check does not detect editable installs because
    # the site packages dir only contains a reference to the source files,
    # not the actual files. That means currently editable installs get a
    # source type UNKNOWN which might or might not lead to issues.

    return False


def get_source_type(module: ModuleType) -> SourceType:
    """Get the type of a source.

    Args:
        module: The module for which to get the source type.

    Returns:
        The source type.
    """
    if module.__name__ in _notebook_modules:
        return SourceType.NOTEBOOK

    try:
        file_path = inspect.getfile(module)
    except (TypeError, OSError):
        if module.__name__ == "__main__" and Environment.in_notebook():
            return SourceType.NOTEBOOK

        return SourceType.BUILTIN

    if is_internal_module(module_name=module.__name__):
        return SourceType.INTERNAL

    if is_distribution_package_file(
        file_path=file_path, module_name=module.__name__
    ):
        return SourceType.DISTRIBUTION_PACKAGE

    if is_standard_lib_file(file_path=file_path):
        return SourceType.BUILTIN

    # Make sure to check for distribution packages before this to catch the
    # case when a virtual environment is inside our source root
    if is_user_file(file_path=file_path):
        return SourceType.USER

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


def _warn_about_potential_source_loading_issues(
    source: CodeRepositorySource,
) -> None:
    """Warn about potential issues when loading the code repository source.

    Args:
        source: The code repository source.
    """
    from zenml.utils import code_repository_utils

    local_repo = code_repository_utils.find_active_code_repository()

    if not local_repo:
        logger.warning(
            "Potential issue when loading the source `%s`: The source "
            "references the code repository `%s` which is not active at the "
            "current source root `%s`. The source loading might fail or load "
            "your local code which might differ from the one used when the "
            "source was originally stored.",
            source.import_path,
            source.repository_id,
            get_source_root(),
        )
    elif local_repo.code_repository_id != source.repository_id:
        logger.warning(
            "Potential issue when loading the source `%s`: The source "
            "references the code repository `%s` but there is a different "
            "code repository `%s` active at the current source root `%s`. The "
            "source loading might fail or load "
            "your local code which might differ from the one used when the "
            "source was originally stored.",
            source.import_path,
            source.repository_id,
            local_repo.code_repository_id,
            get_source_root(),
        )
    elif local_repo.current_commit != source.commit:
        logger.warning(
            "Potential issue when loading the source `%s`: The source "
            "references the commit `%s` of code repository `%s` but your local "
            "code is at commit `%s`. The source loading might fail or load "
            "your local code which might differ from the one used when the "
            "source was originally stored.",
            source.import_path,
            source.commit,
            source.repository_id,
            local_repo.current_commit,
        )
    elif local_repo.is_dirty:
        logger.warning(
            "Potential issue when loading the source `%s`: The source "
            "references the commit `%s` of code repository `%s` but your local "
            "repository contains uncommitted changes. The source loading might "
            "fail or load your local code which might differ from the one used "
            "when the source was originally stored.",
            source.import_path,
            source.commit,
            source.repository_id,
        )


def _resolve_module(module: ModuleType) -> str:
    """Resolve a module.

    Args:
        module: The module to resolve.

    Raises:
        RuntimeError: If the module resolving failed.

    Returns:
        The resolved module import path.
    """
    if not hasattr(module, "__file__") or not module.__file__:
        if module.__name__ == "__main__" and not Environment.in_notebook():
            raise RuntimeError(
                f"Unable to resolve module `{module}` because it was "
                "not loaded from a file."
            )
        return module.__name__

    module_file = Path(module.__file__).resolve()
    source_root = Path(get_source_root()).resolve()

    if source_root not in module_file.parents:
        raise RuntimeError(
            f"Unable to resolve module `{module}`. The file from which the "
            f"module was loaded ({module_file}) is outside the source root "
            f"({source_root})."
        )

    if module_file.suffix != ".py":
        raise RuntimeError(
            f"Unable to resolve module `{module}`. The file from which the "
            f"module was loaded ({module_file}) is not a python file."
        )

    module_source_path = module_file.relative_to(source_root).with_suffix("")
    module_source = str(module_source_path).replace(os.path.sep, ".")

    logger.debug("Resolved module `%s` to `%s`", module, module_source)

    return module_source


def _load_module(
    module_name: str, import_root: Optional[str] = None
) -> ModuleType:
    """Load a module.

    Args:
        module_name: The name of the module to load.
        import_root: The import root to use for loading the module. If given,
            will be prepended to the Python path before trying to import the
            module.

    Returns:
        The imported module.
    """
    if import_root:
        with prepend_python_path(import_root):
            return importlib.import_module(module_name)
    else:
        return importlib.import_module(module_name)


def _get_shared_temp_dir() -> str:
    """Get path to a shared temporary directory.

    Returns:
        Path to a shared temporary directory.
    """
    global _SHARED_TEMPDIR

    if not _SHARED_TEMPDIR:
        import tempfile

        _SHARED_TEMPDIR = tempfile.mkdtemp()

    return _SHARED_TEMPDIR


def _try_to_load_notebook_source(source: NotebookSource) -> Any:
    """Helper function to load a notebook source outside of a notebook.

    Args:
        source: The source to load.

    Raises:
        RuntimeError: If the source can't be loaded.
        FileNotFoundError: If the file containing the notebook cell code can't
            be found.

    Returns:
        The loaded object.
    """
    if not source.replacement_module:
        raise RuntimeError(
            f"Failed to load {source.import_path}. This object was defined in "
            "a notebook and you're trying to load it outside of a notebook. "
            "This is currently only enabled for ZenML steps and materializers. "
            "To enable this for your custom classes or functions, use the "
            "`zenml.utils.notebook_utils.enable_notebook_code_extraction` "
            "decorator."
        )

    extract_dir = _get_shared_temp_dir()
    file_name = f"{source.replacement_module}.py"
    file_path = os.path.join(extract_dir, file_name)

    if not os.path.exists(file_path):
        from zenml.client import Client
        from zenml.utils import code_utils

        artifact_store = Client().active_stack.artifact_store

        if (
            source.artifact_store_id
            and source.artifact_store_id != artifact_store.id
        ):
            raise RuntimeError(
                "Notebook cell code not stored in active artifact store."
            )

        logger.info(
            "Downloading notebook cell content to load `%s`.",
            source.import_path,
        )

        try:
            code_utils.download_notebook_code(
                artifact_store=artifact_store,
                file_name=file_name,
                download_path=file_path,
            )
        except FileNotFoundError:
            if not source.artifact_store_id:
                raise FileNotFoundError(
                    "Unable to find notebook code file. This might be because "
                    "the file is stored in a different artifact store."
                )

            raise
        else:
            _notebook_modules[source.replacement_module] = artifact_store.id
    try:
        module = _load_module(
            module_name=source.replacement_module, import_root=extract_dir
        )
    except ImportError:
        raise RuntimeError(
            f"Unable to load {source.import_path}. This object was defined in "
            "a notebook and you're trying to load it outside of a notebook. "
            "To enable this, ZenML extracts the code of your cell into a "
            "python file. This means your cell code needs to be "
            "self-contained:\n"
            "  * All required imports must be done in this cell, even if the "
            "same imports already happen in previous notebook cells.\n"
            "  * The cell can't use any code defined in other notebook cells."
        )

    if source.attribute:
        obj = getattr(module, source.attribute)
    else:
        obj = module

    # Store the original notebook source so resolving this object works as
    # expected
    setattr(obj, ZENML_SOURCE_ATTRIBUTE_NAME, source)

    return obj


def _get_package_for_module(module_name: str) -> Optional[str]:
    """Get the package name for a module.

    Args:
        module_name: The module name.

    Returns:
        The package name or None if no package was found.
    """
    if sys.version_info < (3, 10):
        from importlib_metadata import packages_distributions
    else:
        from importlib.metadata import packages_distributions

    top_level_module = module_name.split(".", maxsplit=1)[0]
    package_names = packages_distributions().get(top_level_module, [])

    if len(package_names) == 1:
        return package_names[0]

    # TODO: maybe handle packages which share the same top-level import
    return None


def _get_package_version(package_name: str) -> Optional[str]:
    """Gets the version of a package.

    Args:
        package_name: The name of the package for which to get the version.

    Returns:
        The package version or None if fetching the version failed.
    """
    if sys.version_info < (3, 10):
        from importlib_metadata import PackageNotFoundError, version

        version = cast(Callable[..., str], version)
    else:
        from importlib.metadata import PackageNotFoundError, version

    try:
        return version(distribution_name=package_name)
    except (ValueError, PackageNotFoundError):
        return None


# Ideally both the expected_class and return type should be annotated with a
# type var to indicate that both they represent the same type. However, mypy
# currently doesn't support this for abstract classes:
# https://github.com/python/mypy/issues/4717
def load_and_validate_class(
    source: Union[str, Source], expected_class: Type[Any]
) -> Type[Any]:
    """Loads a source class and validates its class.

    Args:
        source: The source.
        expected_class: The class that the source should resolve to.

    Raises:
        TypeError: If the source does not resolve to the expected class.

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
    """Validates that a source resolves to a certain class.

    Args:
        source: The source to validate.
        expected_class: The class that the source should resolve to.

    Returns:
        True if the source resolves to the expected class, False otherwise.
    """
    try:
        obj = load(source)
    except Exception:
        return False

    if isinstance(obj, type) and issubclass(obj, expected_class):
        return True
    else:
        return False


def get_resolved_notebook_sources() -> Dict[str, str]:
    """Get all notebook sources that were resolved in this process.

    Returns:
        Dictionary mapping the import path of notebook sources to the code
        of their notebook cell.
    """
    return _resolved_notebook_sources.copy()


def _should_load_from_main_module(source: Source) -> bool:
    """Check whether the source should be loaded from the main module.

    Args:
        source: The source to check.

    Returns:
        If the source should be loaded from the main module instead of the
        module defined in the source object.
    """
    try:
        resolved_main_module = _resolve_module(sys.modules["__main__"])
    except RuntimeError:
        return False

    return resolved_main_module == source.module
