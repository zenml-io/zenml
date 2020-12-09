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

import logging
from typing import Text, Type

from tfx.utils.import_utils import import_class_by_path

from zenml.core.repo.git_wrapper import GitWrapper
from zenml.core.repo.repo import Repository
from zenml.utils.constants import APP_NAME
from zenml.utils.version import __release__


def create_zenml_pin():
    """Creates a ZenML pin for source pinning from release version."""
    return f'{APP_NAME}_{__release__}'


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
    r: Repository = Repository.get_instance()
    wrapper: GitWrapper = r.get_git_wrapper()
    source_path = wrapper.resolve_source_path(source_path)
    return source_path


def load_source_path_class(source_path: Text) -> Type:
    """
    Loads a Python class from the path provided.

    Args:
        source_path (str): relative module path e.g. this.module.Class[@sha]
    """
    r: Repository = Repository.get_instance()
    pin = source_path.split('@')[-1]
    source = source_path.split('@')[0]
    is_standard = is_standard_pin(pin)

    if '@' in source_path and not is_standard:
        logging.info('Pinned step found with git sha. '
                     'Loading class from git history.')
        wrapper: GitWrapper = r.get_git_wrapper()

        # Get reference to current sha
        active_branch = wrapper.git_repo.active_branch.name

        # critical step
        logging.warning('Found source with a pinned sha. Will now stash '
                        'current changes and keep executing.')
        try:
            wrapper.stash()
        except Exception:
            # we need to make sure that an unsafe operation did not happen
            # TODO: [HIGH] Implement proper exception handling here.
            raise Exception

        try:
            wrapper.checkout(pin)
        except Exception:
            # popping needs to happen in any case
            wrapper.checkout(active_branch)
            wrapper.stash_pop()
            raise Exception

        class_ = import_class_by_path(source)
        wrapper.checkout(active_branch)
        wrapper.stash_pop()
    elif '@' in source_path and is_standard:
        logging.info(f'Default {APP_NAME} class used. Loading directly.')
        # TODO: [LOW] Check if ZenML version is installed before loading.
        class_ = import_class_by_path(source)
    else:
        logging.info('Unpinned step found with no git sha. Attempting to '
                     'load class from current repository state.')
        class_ = import_class_by_path(source)

    return class_
