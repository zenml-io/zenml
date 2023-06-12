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
"""Class to handle stack recipe download and cleanup."""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from zenml.constants import STACK_RECIPES_REPO_DIR
from zenml.logger import get_logger
from zenml.recipes.models import StackRecipe, StackRecipeRepo
from zenml.utils import io_utils

logger = get_logger(__name__)

EXCLUDED_RECIPE_DIRS = [""]


class GitStackRecipesHandler:
    """Class for the `GitStackRecipesHandler` that interfaces with the CLI."""

    def __init__(self) -> None:
        """Create a new GitStackRecipesHandler instance."""
        self.repo_dir = io_utils.get_global_config_directory()
        self.stack_recipes_dir = Path(
            os.path.join(self.repo_dir, STACK_RECIPES_REPO_DIR)
        )
        self.stack_recipe_repo = StackRecipeRepo(self.stack_recipes_dir)

    @property
    def stack_recipes(self) -> List[StackRecipe]:
        """Property that contains a list of stack recipes.

        Returns:
            A list of stack recipes.
        """
        return [
            StackRecipe(name, Path(os.path.join(self.stack_recipes_dir, name)))
            for name in sorted(os.listdir(self.stack_recipes_dir))
            if (
                not name.startswith(".")
                and not name.startswith("__")
                and not name == "LICENSE"
                and not name.endswith(".md")
                and not name.endswith(".sh")
                and not name == "modules"
            )
        ]

    def is_stack_recipe(self, stack_recipe_name: Optional[str] = None) -> bool:
        """Checks if the given stack_recipe_name corresponds to a stack_recipe.

        Args:
            stack_recipe_name: The name of the stack_recipe to check.

        Returns:
            Whether the supplied stack_recipe_name corresponds to a
            stack recipe.
        """
        stack_recipe_dict = {
            recipe.name: recipe for recipe in self.stack_recipes
        }
        if stack_recipe_name:
            if stack_recipe_name in stack_recipe_dict.keys():
                return True

        return False

    def get_stack_recipes(
        self, stack_recipe_name: Optional[str] = None
    ) -> List[StackRecipe]:
        """Method that allows you to get a stack recipe by name.

        If no stack recipe is supplied,  all stack recipes are returned.

        Args:
            stack_recipe_name: Name of an stack recipe.

        Returns:
            A list of stack recipes.

        Raises:
            KeyError: If the supplied stack_recipe_name is not found.
        """
        stack_recipe_dict = {
            recipe.name: recipe
            for recipe in self.stack_recipes
            if recipe.name not in EXCLUDED_RECIPE_DIRS
        }
        if stack_recipe_name:
            if stack_recipe_name in stack_recipe_dict.keys():
                return [stack_recipe_dict[stack_recipe_name]]
            else:
                raise KeyError(
                    f"Stack recipe {stack_recipe_name} does not exist! "
                    f"Available Stack Recipes: {list(stack_recipe_dict)}"
                    "If you want to deploy a custom stack recipe available "
                    "locally, please call deploy with the `--skip-pull` flag "
                    "and specify the path to the stack recipe directory with "
                    "the `--path` or `-p` flag."
                )
        else:
            return self.stack_recipes

    def pull(
        self,
        branch: str = "develop",
        force: bool = False,
    ) -> None:
        """Pulls the stack recipes from the main git stack recipes repository.

        Args:
            branch: The name of the branch to pull from.
            force: Whether to force the pull.
        """
        from git.exc import GitCommandError

        if not self.stack_recipe_repo.is_cloned:
            self.stack_recipe_repo.clone()
        elif force:
            self.stack_recipe_repo.delete()
            self.stack_recipe_repo.clone()

        try:
            self.stack_recipe_repo.checkout(branch=branch)
        except GitCommandError:
            logger.warning(
                f"The specified branch {branch} not found in "
                "repo, falling back to the latest release."
            )
            self.stack_recipe_repo.checkout_latest_release()

    def pull_latest_stack_recipes(self) -> None:
        """Pulls the latest stack recipes from the stack recipes repository."""
        self.pull(
            branch=self.stack_recipe_repo.latest_release_branch, force=True
        )

    def copy_stack_recipe(
        self, stack_recipe: StackRecipe, destination_dir: str
    ) -> None:
        """Copies a stack recipe to the destination_dir.

        Args:
            stack_recipe: The stack recipe to copy.
            destination_dir: The destination directory to copy the recipe to.
        """
        io_utils.create_dir_if_not_exists(destination_dir)
        io_utils.copy_dir(
            str(stack_recipe.path_in_repo),
            destination_dir,
            overwrite=True,
        )

    @staticmethod
    def clean_current_stack_recipes() -> None:
        """Deletes the stack recipes directory from your working directory."""
        stack_recipes_directory = os.path.join(
            os.getcwd(), "zenml_stack_recipes"
        )
        shutil.rmtree(stack_recipes_directory)

    def get_active_version(self) -> Optional[str]:
        """Returns the active version of the mlstacks repository.

        Returns:
            The active version of the repository.
        """
        self.stack_recipe_repo.checkout_latest_release()
        return self.stack_recipe_repo.active_version
