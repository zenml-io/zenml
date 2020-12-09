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

import logging
import os
from typing import Text, List

from git import Repo as GitRepo

from zenml.core.repo.constants import GIT_FOLDER_NAME
from zenml.utils import path_utils


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
        for item in self.git_repo.index.diff(None):
            # These are all changed files
            if file_path == item.a_path:
                return False
        return True

    def get_current_sha(self) -> Text:
        """
        Finds the git sha that each file within the module is currently on.

        Args:
            module_path (str): Path to any module within the ZenML repo.
        """
        # TODO: [HIGH] Check whether returning the head makes sense.
        return self.git_repo.head.object.hexsha

    def resolve_source_path(self, source_path: Text) -> Text:
        """
        Takes source path (e.g. this.module.ClassName), and appends relevant
        sha to it if the files within `module` are all committed. If even one
        file is not committed, then returns `source_path` unchanged.

        Args:
            source_path (str): relative module path pointing to a Class.
        """
        # import here to resolve circular dependency
        from zenml.utils.source_utils import get_path_from_source
        file_path = get_path_from_source(source_path)

        if not self.check_file_committed(file_path):
            logging.warning(f'Found uncommitted file {file_path}. '
                            f'Pipelines run with this configuration '
                            f'may not be reproducible. Please commit all '
                            f'files '
                            f'in this module and then run the pipeline to '
                            f'ensure reproducibility.')
            return source_path
        return source_path + '@' + self.get_current_sha()

    def stash(self):
        """Wrapper for git stash"""
        git = self.git_repo.git
        git.stash()

    def stash_pop(self):
        """Wrapper for git stash pop. Only pops if there's something to pop."""
        git = self.git_repo.git
        if git.stash('list') != '':
            git.stash('pop')

    def checkout(self, sha_or_branch_name: Text):
        """
        Wrapper for git checkout

        Args:
            sha_or_branch_name: hex string of len 40 representing git sha OR
            name of branch
        """
        # TODO: [HIGH] Implement exception handling
        git = self.git_repo.git
        git.checkout(sha_or_branch_name)
