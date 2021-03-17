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
"""Wrapper class to handle Git integration"""

import os
from typing import Text, List

from git import Repo as GitRepo, BadName

from zenml.logger import get_logger
from zenml.repo.constants import GIT_FOLDER_NAME
from zenml.utils import path_utils

logger = get_logger(__name__)


class GitWrapper:
    """Wrapper class for Git.

    This class is responsible for handling git interactions, primarily
    handling versioning of different steps in pipelines.
    """

    def __init__(self, repo_path: Text):
        """
        Initialize GitWrapper. Should be initialize by ZenML Repository.
        Args:
            repo_path:

        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.
        """
        # TODO: [LOW] Raise ZenML exceptions here instead.
        self.repo_path: Text = repo_path
        self.git_root_path: Text = os.path.join(repo_path, GIT_FOLDER_NAME)
        self.git_repo: GitRepo = GitRepo(self.repo_path)

        # TODO: [LOW] Check whether this is necessary.
        assert not self.git_repo.bare

    def add_gitignore(self, items: List[Text]):
        """
        Adds `items` to .gitignore, if .gitignore exists. Otherwise creates
        and adds.

        Args:
            items (list[str]): Items to add.
        """
        str_items = '\n'.join(items)
        str_items = '\n\n# ZenML\n' + str_items

        gitignore_path = os.path.join(self.repo_path, '.gitignore')
        if not path_utils.file_exists(gitignore_path):
            path_utils.create_file_if_not_exists(gitignore_path, str_items)
        else:
            path_utils.append_file(gitignore_path, str_items)

    def check_file_committed(self, file_path: Text) -> bool:
        """
        Checks file is committed. If yes, return True, else False.

        Args:
            file_path (str): Path to any file within the ZenML repo.
        """
        uncommitted_files = [i.a_path for i in self.git_repo.index.diff(None)]
        try:
            staged_files = [i.a_path for i in self.git_repo.index.diff('HEAD')]
        except BadName:
            # for Ref 'HEAD' did not resolve to an object
            logger.debug('No committed files in the repo. No staged files.')
            staged_files = []

        # source: https://stackoverflow.com/questions/3801321/
        untracked_files = self.git_repo.git.ls_files(
            others=True, exclude_standard=True).split('\n')
        for item in uncommitted_files + staged_files + untracked_files:
            # These are all changed files
            if file_path == item:
                return False
        return True

    def get_current_sha(self) -> Text:
        """
        Finds the git sha that each file within the module is currently on.
        """
        return self.git_repo.head.object.hexsha

    def check_module_clean(self, source: Text):
        """
        Returns True if all files within source's module are committed.

        Args:
            source (str): relative module path pointing to a Class.
        """
        # import here to resolve circular dependency
        from zenml.utils import source_utils

        # Get the module path
        module_path = source_utils.get_module_source_from_source(source)

        # Get relative path of module because check_file_committed needs that
        module_dir = source_utils.get_relative_path_from_module_source(
            module_path)

        # Get absolute path of module because path_utils.list_dir needs that
        mod_abs_dir = source_utils.get_absolute_path_from_module_source(
            module_path)
        module_file_names = path_utils.list_dir(
            mod_abs_dir, only_file_names=True)

        # Go through each file in module and see if there are uncommitted ones
        for file_path in module_file_names:
            path = os.path.join(module_dir, file_path)

            # if its .gitignored then continue and dont do anything
            if len(self.git_repo.ignored(path)) > 0:
                continue

            if path_utils.is_dir(os.path.join(mod_abs_dir, file_path)):
                logger.warning(
                    f'The step {source} is contained inside a module '
                    f'that '
                    f'has sub-directories (the sub-directory {file_path} at '
                    f'{mod_abs_dir}). For now, ZenML supports only a flat '
                    f'directory structure in which to place Steps. Please make'
                    f' sure that the Step does not utilize the sub-directory.')
            if not self.check_file_committed(path):
                return False
        return True

    def resolve_class_source(self, source: Text) -> Text:
        """
        Takes source (e.g. this.module.ClassName), and appends relevant
        sha to it if the files within `module` are all committed. If even one
        file is not committed, then returns `source` unchanged.

        Args:
            source (str): relative module path pointing to a Class.
        """
        if not self.check_module_clean(source):
            # Return the source path if not clean
            logger.warning(
                f'Found uncommitted file. Pipelines run with this '
                f'configuration may not be reproducible. Please commit '
                f'all files in this module and then run the pipeline to '
                f'ensure reproducibility.')
            return source
        return source + '@' + self.get_current_sha()

    def stash(self):
        """Wrapper for git stash"""
        git = self.git_repo.git
        git.stash()

    def stash_pop(self):
        """Wrapper for git stash pop. Only pops if there's something to pop."""
        git = self.git_repo.git
        if git.stash('list') != '':
            git.stash('pop')

    def checkout(self, sha_or_branch: Text = None, directory: Text = None):
        """
        Wrapper for git checkout

        Args:
            sha_or_branch: hex string of len 40 representing git sha OR
            name of branch
            directory (str): relative path to directory to scope checkout
        """
        # TODO: [MEDIUM] Implement exception handling
        git = self.git_repo.git
        if sha_or_branch is None:
            # Checks out directory at sha_or_branch
            assert directory is not None
            git.checkout('--', directory)
        elif directory is not None:
            assert sha_or_branch is not None
            # Basically discards all changes in directory
            git.checkout(sha_or_branch, '--', directory)
        else:
            # The case where sha_or_branch is not None and directory is None
            # In this case, the whole repo is checked out at sha_or_branch
            git.checkout(sha_or_branch)

    def reset(self, directory: Text = None):
        """
        Wrapper for `git reset HEAD <directory>`.

        Args:
            directory (str): relative path to directory to scope checkout
        """
        git = self.git_repo.git
        git.reset('HEAD', directory)
