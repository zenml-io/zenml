#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
from typing import Text, Type, Optional, Union

from tfx.utils.import_utils import import_class_by_path

from zenml.constants import APP_NAME
from zenml.logger import get_logger
from zenml.repo import GitWrapper
from zenml.repo.repo import Repository
from zenml.version import __version__

logger = get_logger(__name__)


def is_standard_pin(pin: Text) -> bool:
    """
    Returns True if pin is valid ZenML pin, else False.

    Args:
        pin (str): potential ZenML pin like 'zenml_0.1.1'
    """
    if pin.startswith(f'{APP_NAME}_'):
        return True
    return False


def create_zenml_pin():
    """Creates a ZenML pin for source pinning from release version."""
    return f'{APP_NAME}_{__version__}'


def resolve_standard_source(source: Text) -> Text:
    """
    Creates a ZenML pin for source pinning from release version.

    Args:
        source (str): class_source e.g. this.module.Class.
    """
    if '@' in source:
        raise AssertionError(f'source {source} is already pinned.')
    pin = create_zenml_pin()
    return f'{source}@{pin}'


def is_standard_source(source: Text) -> bool:
    """
    Returns True if source is a standard ZenML source.

    Args:
        source (str): class_source e.g. this.module.Class[@pin].
    """
    if source.split('.')[0] == 'zenml':
        return True
    return False


def is_valid_source(source: Text) -> bool:
    """
    Checks whether the source_path is valid or not.

    Args:
        source (str): class_source e.g. this.module.Class[@pin].
    """
    try:
        load_source_path_class(source)
    except:
        return False
    return True


def get_path_from_source(source):
    """
    Get file path from source

    Args:
        source (str): class_source e.g. this.module.Class.
    """
    # TODO: [MEDIUM] Make sure this is an absolute path rather than naive split
    file_path = "/".join(source.split('.')[:-1]) + '.py'
    return file_path


def get_pin_from_source(source: Text) -> Optional[Text]:
    """
    Gets pin from source, i.e. module.path@pin, returns pin.

    Args:
        source (str): class_source e.g. this.module.Class[@pin].
    """
    if '@' in source:
        pin = source.split('@')[-1]
        return pin
    return 'unpinned'


def get_class_source_from_source(source: Text) -> Optional[Text]:
    """
    Gets class source from source, i.e. module.path@version, returns version.

    Args:
        source: source pointing to potentially pinned sha.
    """
    # source need not even be pinned
    return source.split('@')[0]


def get_module_source_from_source(source: Text) -> Text:
    """
    Gets module source from source. E.g. `some.module.file.class@version`,
    returns `some.module`.

    Args:
        source: source pointing to potentially pinned sha.
    """
    class_source = get_class_source_from_source(source)
    return '.'.join(class_source.split('.')[:-2])


def get_module_source_from_file_path(file_path):
    """
    Gets module_source from a file_path. E.g. `/home/myrepo/step/trainer.py`
    returns `myrepo.step.trainer` if `myrepo` is the root of the repo.

    Args:
        file_path: Absolute file path to a file within the module.
    """
    repo_path = Repository.get_instance().path

    # Replace repo_path with file_path to get relative path left over
    relative_file_path = file_path.replace(repo_path, '')[1:]

    # Kick out the .py and replace `/` with `.` to get the module source
    relative_file_path = relative_file_path.replace('.py', '')
    module_source = relative_file_path.replace('/', '.')
    return module_source


def get_relative_path_from_module_source(module_source: Text):
    """
    Get a directory path from module, relative to root of repository.

    E.g. zenml.core.step will return zenml/core/step.

    Args:
        module_source (str): A module e.g. zenml.core.step
    """
    return module_source.replace('.', '/')


def get_absolute_path_from_module_source(module: Text):
    """
    Get a directory path from module source.

    E.g. `zenml.core.step` will return `full/path/to/zenml/core/step`.

    Args:
        module (str): A module e.g. `zenml.core.step`.
    """
    mod = importlib.import_module(module)
    return mod.__path__[0]


def get_module_source_from_class(class_: Union[Type, Text]) -> Optional[Text]:
    """
    Takes class input and returns module_source. If class is already string
    then returns the same.

    Args:
        class_: object of type class.
    """
    if type(class_) == str:
        module_source = class_
    else:
        # Infer it from the class provided
        if not inspect.isclass(class_):
            raise Exception('step_type is neither string nor class.')
        module_source = class_.__module__ + '.' + class_.__name__
    return module_source


def resolve_class(class_: Type) -> Text:
    """
    Resolves
    Args:
        class_: A Python Class reference.

    Returns: source_path e.g. this.module.Class[@pin].
    """
    initial_source = class_.__module__ + '.' + class_.__name__
    if is_standard_source(initial_source):
        return resolve_standard_source(initial_source)

    # Get the full module path relative to the repository
    file_path = inspect.getfile(class_)
    module_source = get_module_source_from_file_path(file_path)

    class_source = module_source + '.' + class_.__name__
    return resolve_class_source(class_source)


def resolve_class_source(class_source: Text) -> Text:
    """
    Resolves class_source with an optional pin.

    Args:
        class_source (str): class_source e.g. this.module.Class
    """
    if '@' in class_source:
        # already pinned
        return class_source

    if is_standard_source(class_source):
        # that means use standard version
        return resolve_standard_source(class_source)

    # otherwise use Git resolution
    wrapper: GitWrapper = Repository.get_instance().get_git_wrapper()
    resolved_source = wrapper.resolve_class_source(class_source)
    return resolved_source


def load_source_path_class(source: Text) -> Type:
    """
    Loads a Python class from the source.

    Args:
        source (str): class_source e.g. this.module.Class[@sha]
    """
    source = source.split('@')[0]
    pin = source.split('@')[-1]
    is_standard = is_standard_pin(pin)

    if '@' in source and not is_standard:
        logger.debug('Pinned step found with git sha. '
                     'Loading class from git history.')
        wrapper: GitWrapper = Repository.get_instance().get_git_wrapper()

        module_source = get_module_source_from_source(source)
        relative_module_path = get_relative_path_from_module_source(
            module_source)

        logger.warning('Found source with a pinned sha. Will now checkout '
                       f'module: {module_source}')

        # critical step
        if not wrapper.check_module_clean(source):
            raise Exception(f'One of the files at {relative_module_path} '
                            f'is not committed and we '
                            f'are trying to load that directory from git '
                            f'history due to a pinned step in the pipeline. '
                            f'Please commit the file and then run the '
                            f'pipeline.')

        # Check out the directory at that sha
        wrapper.checkout(sha_or_branch=pin, directory=relative_module_path)

        # After this point, all exceptions will first undo the above
        try:
            class_ = import_class_by_path(source)
            wrapper.reset(relative_module_path)
            wrapper.checkout(directory=relative_module_path)
        except Exception:
            wrapper.reset(relative_module_path)
            wrapper.checkout(directory=relative_module_path)
            raise Exception
    elif '@' in source and is_standard:
        logger.debug(f'Default {APP_NAME} class used. Loading directly.')
        # TODO: [LOW] Check if ZenML version is installed before loading.
        class_ = import_class_by_path(source)
    else:
        logger.debug('Unpinned step found with no git sha. Attempting to '
                     'load class from current repository state.')
        class_ = import_class_by_path(source)

    return class_
