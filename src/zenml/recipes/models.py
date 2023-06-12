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
"""Stack Recipe models."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, cast

from zenml.exceptions import GitNotFoundError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import yaml_utils

logger = get_logger(__name__)

STACK_RECIPES_GITHUB_REPO = "https://github.com/zenml-io/mlops-stacks.git"


class LocalStackRecipe:
    """Class to encapsulate the local recipe that can be run from the CLI."""

    def __init__(self, path: Path, name: str) -> None:
        """Create a new LocalStack instance.

        Args:
            name: The name of the stack, specifically the name of the folder
                  on git
            path: Path at which the stack is installed
        """
        self.name = name
        self.path = path

    def is_present(self) -> bool:
        """Checks if the stack_recipe exists at the given path.

        Returns:
            True if the stack_recipe exists at the given path, else False.
        """
        return fileio.isdir(str(self.path))

    @property
    def locals_content(self) -> str:
        """Returns the locals.tf content associated with a particular recipe.

        Returns:
            The locals.tf content associated with a particular recipe.

        Raises:
            ValueError: If the locals.tf file is not found.
            FileNotFoundError: If the locals.tf file is not one of the options.
        """
        locals_file = os.path.join(self.path, "locals.tf")
        try:
            with open(locals_file) as locals:
                locals_content = locals.read()
            return locals_content
        except FileNotFoundError:
            if fileio.exists(str(self.path)) and fileio.isdir(str(self.path)):
                raise ValueError(f"No locals.tf file found in " f"{self.path}")
            else:
                raise FileNotFoundError(
                    f"Recipe {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available recipes, type: `zenml stack recipe "
                    f"list`"
                )


class StackRecipe:
    """Class for all stack recipe objects."""

    def __init__(self, name: str, path_in_repo: Path) -> None:
        """Create a new StackRecipe instance.

        Args:
            name: The name of the recipe, specifically the name of the folder
                  on git
            path_in_repo: Path to the local recipe within the global zenml
                  folder.
        """
        self.name = name
        self.path_in_repo = path_in_repo

    @property
    def readme_content(self) -> str:
        """Returns the README content associated with a particular recipe.

        Returns:
            The README content associated with a particular recipe.

        Raises:
            ValueError: If the README file is not found.
            FileNotFoundError: If the README file is not one of the options.
        """
        readme_file = os.path.join(self.path_in_repo, "README.md")
        try:
            with open(readme_file) as readme:
                readme_content = readme.read()
            return readme_content
        except FileNotFoundError:
            if fileio.exists(str(self.path_in_repo)) and fileio.isdir(
                str(self.path_in_repo)
            ):
                raise ValueError(
                    f"No README.md file found in " f"{self.path_in_repo}"
                )
            else:
                raise FileNotFoundError(
                    f"Recipe {self.name} is not one of the available options."
                    f"\n"
                    f"To list all available recipes, type: `zenml stack recipe "
                    f"list`"
                )

    @property
    def metadata(self) -> Dict[str, Any]:
        """Returns the metadata associated with a particular recipe.

        Returns:
            The metadata associated with a particular recipe.
        """
        metadata = yaml_utils.read_yaml(
            file_path=os.path.join(self.path_in_repo, "metadata.yaml")
        )
        return cast(Dict[str, Any], metadata)


class StackRecipeRepo:
    """Class that represents the stack recipes repo."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new StackRecipeRepo instance.

        Args:
            cloning_path: Path to the local stack recipe repository.

        Raises:
            GitNotFoundError: If git is not installed.
        """
        self.cloning_path = cloning_path

        try:
            from git.exc import InvalidGitRepositoryError, NoSuchPathError
            from git.repo.base import Repo
        except ImportError as e:
            logger.error(
                "In order to use the CLI tool to interact with our recipes, "
                "you need to have an installation of Git on your machine."
            )
            raise GitNotFoundError(e)

        try:
            self.repo = Repo(self.cloning_path)
        except (NoSuchPathError, InvalidGitRepositoryError):
            self.repo = None  # type: ignore
            logger.debug(
                f"`Cloning_path`: {self.cloning_path} was empty, "
                "Automatically cloning the recipes."
            )
            self.clone()
            self.checkout_latest_release()

    @property
    def active_version(self) -> Optional[str]:
        """Returns the active version of the repository.

        In case a release branch is checked out, this property returns
        that version as a string, else `None` is returned.

        Returns:
            The active version of the repository.
        """
        for branch in self.repo.heads:
            if (
                branch.name.startswith("release/")
                and branch.commit == self.repo.head.commit
            ):
                return branch.name[len("release/") :]

        return None

    @property
    def latest_release_branch(self) -> str:
        """Returns the name of the latest release branch.

        Returns:
            The name of the latest release branch.
        """
        from packaging.version import Version, parse

        tags = sorted(
            self.repo.tags,
            key=lambda t: t.commit.committed_datetime,
        )

        if not tags:
            return "main"

        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"

        latest_release_version: str = tags[-1].name
        return f"release/{latest_release_version}"

    @property
    def is_cloned(self) -> bool:
        """Returns whether we have already cloned the repository.

        Returns:
            Whether we have already cloned the repository.
        """
        return self.cloning_path.exists()

    def clone(self) -> None:
        """Clones repo to `cloning_path`.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system.
        """
        self.cloning_path.mkdir(parents=True, exist_ok=False)
        try:
            from git.repo.base import Repo

            logger.info(f"Downloading recipes to {self.cloning_path}")
            self.repo = Repo.clone_from(
                STACK_RECIPES_GITHUB_REPO,
                self.cloning_path,
                branch="main",
            )
        except KeyboardInterrupt:
            self.delete()
            logger.error("Canceled download of recipes.. Rolled back.")

    def delete(self) -> None:
        """Delete `cloning_path` if it exists.

        Raises:
            AssertionError: If `cloning_path` does not exist.
        """
        if self.cloning_path.exists():
            shutil.rmtree(self.cloning_path)
        else:
            raise AssertionError(
                f"Cannot delete the stack recipes repository from "
                f"{self.cloning_path} as it does not exist."
            )

    def checkout(self, branch: str) -> None:
        """Checks out a specific branch or tag of the repository.

        Args:
            branch: The name of the branch or tag to check out.
        """
        logger.info(f"Checking out branch: {branch}")
        self.repo.git.checkout(branch)

    def checkout_latest_release(self) -> None:
        """Checks out the latest release of the repository."""
        self.checkout(branch=self.latest_release_branch)
