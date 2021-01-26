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

import importlib
import inspect
from typing import Text, Type, Optional, Union

from tfx.utils.import_utils import import_class_by_path

from zenml.core.repo.git_wrapper import GitWrapper
from zenml.core.repo.repo import Repository
from zenml.utils.constants import APP_NAME
from zenml.utils.logger import get_logger
from zenml.utils.version import __version__

logger = get_logger(__name__)


def create_zenml_pin():
    """Creates a ZenML pin for source pinning from release version."""
    return f'{APP_NAME}_{__version__}'


def resolve_standard_source_path(source_path: Text) -> Text:
    """Creates a ZenML pin for source pinning from release version."""
    pin = create_zenml_pin()
    return f'{source_path}@{pin}'


def is_standard_pin(pin: Text) -> bool:
    """
    Returns True if pin is valid ZenML pin, else False.

    Args:
        pin (str): potential ZenML pin like 'zenml_0.1.1'
    """
    if pin.startswith(f'{APP_NAME}_'):
        return True
    return False


def is_standard_step(source_path: Text) -> bool:
    """
    Returns True if source_path is a standard ZenML class.

    Args:
        source_path (str): relative module path e.g. this.module.Class
    """
    if source_path.split('.')[0] == 'zenml':
        return True
    return False


def get_path_from_source(source_path):
    """
    Get file path from source

    Args:
        source_path (str): relative module path e.g. this.module.Class
    """
    file_path = "/".join(source_path.split('.')[:-1]) + '.py'
    return file_path


def get_version_from_source(source: Text) -> Optional[Text]:
    """
    Gets version from source, i.e. module.path@version, returns version.

    Args:
        source: source pointing to potentially pinned sha.
    """
    if '@' in source:
        pin = source.split('@')[-1]
        return pin
    return 'unversioned'


def get_class_path_from_source(source: Text) -> Optional[Text]:
    """
    Gets class path from source, i.e. module.path@version, returns version.

    Args:
        source: source pointing to potentially pinned sha.
    """
    return source.split('@')[0]


def get_module_path_from_source(source: Text) -> Text:
    """
    Gets class path from source. E.g. some.module.file.class@version, returns
    some.module.

    Args:
        source: source pointing to potentially pinned sha.
    """
    class_path = get_class_path_from_source(source)
    return '.'.join(class_path.split('.')[:-2])


def get_relative_path_from_module(module: Text):
    """
    Get a directory path from module, relative to root of repository.

    E.g. zenml.core.step will return zenml/core/step.

    Args:
        module (str): A module e.g. zenml.core.step
    """
    return module.replace('.', '/')


def get_absolute_path_from_module(module: Text):
    """
    Get a directory path from module.

    E.g. zenml.core.step will return full/path/to/zenml/core/step.

    Args:
        module (str): A module e.g. zenml.core.step
    """
    mod = importlib.import_module(module)
    return mod.__path__[0]


def get_module_path_from_class(class_: Union[Type, Text]) -> Optional[Text]:
    """
    Takes class input and returns module_path. If class is already string
    then returns the same.

    Args:
        class_: object of type class.
    """
    if type(class_) == str:
        module_path_str = class_
    else:
        # Infer it from the class provided
        if not inspect.isclass(class_):
            raise Exception('step_type is neither string nor class.')
        module_path_str = class_.__module__ + '.' + class_.__name__
    return module_path_str


def resolve_source_path(source_path: Text) -> Text:
    """
    Resolves source path with an optional sha using Git.

    Args:
        source_path (str): relative module path e.g. this.module.Class
    """
    if is_standard_step(source_path):
        # that means use standard version
        return resolve_standard_source_path(source_path)

    # otherwise use Git resolution
    wrapper: GitWrapper = Repository.get_instance().get_git_wrapper()
    source_path = wrapper.resolve_source_path(source_path)
    return source_path


def load_source_path_class(source_path: Text) -> Type:
    """
    Loads a Python class from the path provided.

    Args:
        source_path (str): relative module path e.g. this.module.Class[@sha]
    """
    source = source_path.split('@')[0]
    pin = source_path.split('@')[-1]
    is_standard = is_standard_pin(pin)

    if '@' in source_path and not is_standard:
        logger.debug('Pinned step found with git sha. '
                     'Loading class from git history.')
        wrapper: GitWrapper = Repository.get_instance().get_git_wrapper()

        module_path = get_module_path_from_source(source_path)
        relative_module_path = get_relative_path_from_module(module_path)

        logger.warning('Found source with a pinned sha. Will now checkout '
                       f'module: {module_path}')

        # critical step
        if not wrapper.check_module_clean(source_path):
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
    elif '@' in source_path and is_standard:
        logger.debug(f'Default {APP_NAME} class used. Loading directly.')
        # TODO: [LOW] Check if ZenML version is installed before loading.
        class_ = import_class_by_path(source)
    else:
        logger.debug('Unpinned step found with no git sha. Attempting to '
                     'load class from current repository state.')
        class_ = import_class_by_path(source)

    return class_


def is_source(source_path: Text) -> bool:
    """
    Checks whether the source_path is source or not.

    Args:
        source_path (str): relative module path e.g. this.module.Class[@sha]
    """
    try:
        load_source_path_class(source_path)
    except:
        return False
    return True
