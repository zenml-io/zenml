#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
import inspect
import os
from typing import List, Type

from git import BadName
from git import Repo as GitRepo
from tfx.utils.import_utils import import_class_by_path

from zenml.constants import APP_NAME
from zenml.exceptions import GitException
from zenml.logger import get_logger
from zenml.utils import path_utils, source_utils
from zenml.utils.source_utils import (
    get_module_source_from_file_path,
    get_module_source_from_source,
    get_relative_path_from_module_source,
    is_standard_pin,
    is_standard_source,
    resolve_standard_source,
)

GIT_FOLDER_NAME = ".git"

logger = get_logger(__name__)


class GitWrapper:
    """Wrapper class for Git.

    This class is responsible for handling git interactions, primarily
    handling versioning of different steps in pipelines.
    """

    def __init__(self, repo_path: str):
        """
        Initialize GitWrapper. Should be initialize by ZenML Repository.
        Args:
            repo_path:

        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.
        """
        # TODO: [LOW] Raise ZenML exceptions here instead.
        self.repo_path: str = repo_path
        self.git_root_path: str = os.path.join(repo_path, GIT_FOLDER_NAME)
        self.git_repo: GitRepo = GitRepo(self.repo_path)

    def add_gitignore(self, items: List[str]):
        """
        Adds `items` to .gitignore, if .gitignore exists. Otherwise creates
        and adds.

        Args:
            items (list[str]): Items to add.
        """
        str_items = "\n".join(items)
        str_items = "\n\n# ZenML\n" + str_items

        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        if not path_utils.file_exists(gitignore_path):
            path_utils.create_file_if_not_exists(gitignore_path, str_items)
        else:
            path_utils.append_file(gitignore_path, str_items)

    def check_file_committed(self, file_path: str) -> bool:
        """
        Checks file is committed. If yes, return True, else False.

        Args:
            file_path (str): Path to any file within the ZenML repo.
        """
        uncommitted_files = [i.a_path for i in self.git_repo.index.diff(None)]
        try:
            staged_files = [i.a_path for i in self.git_repo.index.diff("HEAD")]
        except BadName:
            # for Ref 'HEAD' did not resolve to an object
            logger.debug("No committed files in the repo. No staged files.")
            staged_files = []

        # source: https://stackoverflow.com/questions/3801321/
        untracked_files = self.git_repo.git.ls_files(
            others=True, exclude_standard=True
        ).split("\n")
        for item in uncommitted_files + staged_files + untracked_files:
            # These are all changed files
            if file_path == item:
                return False
        return True

    def get_current_sha(self) -> str:
        """
        Finds the git sha that each file within the module is currently on.
        """
        return self.git_repo.head.object.hexsha

    def check_module_clean(self, source: str):
        """
        Returns True if all files within source's module are committed.

        Args:
            source (str): relative module path pointing to a Class.
        """
        # Get the module path
        module_path = source_utils.get_module_source_from_source(source)

        # Get relative path of module because check_file_committed needs that
        module_dir = source_utils.get_relative_path_from_module_source(
            module_path
        )

        # Get absolute path of module because path_utils.list_dir needs that
        mod_abs_dir = source_utils.get_absolute_path_from_module_source(
            module_path
        )
        module_file_names = path_utils.list_dir(
            mod_abs_dir, only_file_names=True
        )

        # Go through each file in module and see if there are uncommitted ones
        for file_path in module_file_names:
            path = os.path.join(module_dir, file_path)

            # if its .gitignored then continue and dont do anything
            if len(self.git_repo.ignored(path)) > 0:
                continue

            if path_utils.is_dir(os.path.join(mod_abs_dir, file_path)):
                logger.warning(
                    f"The step {source} is contained inside a module "
                    f"that "
                    f"has sub-directories (the sub-directory {file_path} at "
                    f"{mod_abs_dir}). For now, ZenML supports only a flat "
                    f"directory structure in which to place Steps. Please make"
                    f" sure that the Step does not utilize the sub-directory."
                )
            if not self.check_file_committed(path):
                return False
        return True

    def stash(self):
        """Wrapper for git stash"""
        git = self.git_repo.git
        git.stash()

    def stash_pop(self):
        """Wrapper for git stash pop. Only pops if there's something to pop."""
        git = self.git_repo.git
        if git.stash("list") != "":
            git.stash("pop")

    def checkout(self, sha_or_branch: str = None, directory: str = None):
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
            git.checkout("--", directory)
        elif directory is not None:
            assert sha_or_branch is not None
            # Basically discards all changes in directory
            git.checkout(sha_or_branch, "--", directory)
        else:
            # The case where sha_or_branch is not None and directory is None
            # In this case, the whole repo is checked out at sha_or_branch
            git.checkout(sha_or_branch)

    def reset(self, directory: str = None):
        """
        Wrapper for `git reset HEAD <directory>`.

        Args:
            directory (str): relative path to directory to scope checkout
        """
        git = self.git_repo.git
        git.reset("HEAD", directory)

    def resolve_class_source(self, class_source: str) -> str:
        """
        Resolves class_source with an optional pin.
        Takes source (e.g. this.module.ClassName), and appends relevant
        sha to it if the files within `module` are all committed. If even one
        file is not committed, then returns `source` unchanged.

        Args:
            class_source (str): class_source e.g. this.module.Class
        """
        if "@" in class_source:
            # already pinned
            return class_source

        if is_standard_source(class_source):
            # that means use standard version
            return resolve_standard_source(class_source)

        # otherwise use Git resolution
        if not self.check_module_clean(class_source):
            # Return the source path if not clean
            logger.warning(
                "Found uncommitted file. Pipelines run with this "
                "configuration may not be reproducible. Please commit "
                "all files in this module and then run the pipeline to "
                "ensure reproducibility."
            )
            return class_source
        return class_source + "@" + self.get_current_sha()

    def is_valid_source(self, source: str) -> bool:
        """
        Checks whether the source_path is valid or not.

        Args:
            source (str): class_source e.g. this.module.Class[@pin].
        """
        try:
            self.load_source_path_class(source)
        except GitException:
            return False
        return True

    def load_source_path_class(self, source: str) -> Type:
        """
        Loads a Python class from the source.

        Args:
            source: class_source e.g. this.module.Class[@sha]
        """
        source = source.split("@")[0]
        pin = source.split("@")[-1]
        is_standard = is_standard_pin(pin)

        if "@" in source and not is_standard:
            logger.debug(
                "Pinned step found with git sha. "
                "Loading class from git history."
            )

            module_source = get_module_source_from_source(source)
            relative_module_path = get_relative_path_from_module_source(
                module_source
            )

            logger.warning(
                "Found source with a pinned sha. Will now checkout "
                f"module: {module_source}"
            )

            # critical step
            if not self.check_module_clean(source):
                raise GitException(
                    f"One of the files at {relative_module_path} "
                    f"is not committed and we "
                    f"are trying to load that directory from git "
                    f"history due to a pinned step in the pipeline. "
                    f"Please commit the file and then run the "
                    f"pipeline."
                )

            # Check out the directory at that sha
            self.checkout(sha_or_branch=pin, directory=relative_module_path)

            # After this point, all exceptions will first undo the above
            try:
                class_ = import_class_by_path(source)
                self.reset(relative_module_path)
                self.checkout(directory=relative_module_path)
            except Exception as e:
                self.reset(relative_module_path)
                self.checkout(directory=relative_module_path)
                raise GitException(
                    f"A git exception occured when checking out repository "
                    f"from git history. Resetting repository to original "
                    f"state. Original exception: {e}"
                )

        elif "@" in source and is_standard:
            logger.debug(f"Default {APP_NAME} class used. Loading directly.")
            # TODO: [LOW] Check if ZenML version is installed before loading.
            class_ = import_class_by_path(source)
        else:
            logger.debug(
                "Unpinned step found with no git sha. Attempting to "
                "load class from current repository state."
            )
            class_ = import_class_by_path(source)

        return class_

    def resolve_class(self, class_: Type) -> str:
        """
        Resolves
        Args:
            class_: A Python Class reference.

        Returns: source_path e.g. this.module.Class[@pin].
        """
        initial_source = class_.__module__ + "." + class_.__name__
        if is_standard_source(initial_source):
            return resolve_standard_source(initial_source)

        # Get the full module path relative to the repository
        file_path = inspect.getfile(class_)
        module_source = get_module_source_from_file_path(file_path)

        class_source = module_source + "." + class_.__name__
        return self.resolve_class_source(class_source)
