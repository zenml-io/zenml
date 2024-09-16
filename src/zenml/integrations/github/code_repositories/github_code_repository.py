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
"""GitHub code repository."""

import os
import re
from typing import List, Optional, Tuple

import requests
from github import Github, GithubException
from github.Repository import Repository

from zenml.code_repositories import (
    BaseCodeRepository,
    LocalRepositoryContext,
)
from zenml.code_repositories.base_code_repository import (
    BaseCodeRepositoryConfig,
)
from zenml.code_repositories.git import LocalGitRepositoryContext
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)


class GitHubCodeRepositoryConfig(BaseCodeRepositoryConfig):
    """Config for GitHub code repositories.

    Args:
        url: The URL of the GitHub instance.
        owner: The owner of the repository.
        repository: The name of the repository.
        host: The host of the repository.
        token: The token to access the repository.
    """

    url: Optional[str]
    owner: str
    repository: str
    host: Optional[str] = "github.com"
    token: Optional[str] = SecretField(default=None)


class GitHubCodeRepository(BaseCodeRepository):
    """GitHub code repository."""

    @property
    def config(self) -> GitHubCodeRepositoryConfig:
        """Returns the `GitHubCodeRepositoryConfig` config.

        Returns:
            The configuration.
        """
        return GitHubCodeRepositoryConfig(**self._config)

    @property
    def github_repo(self) -> Repository:
        """The GitHub repository object from the GitHub API.

        Returns:
            The GitHub repository.

        Raises:
            RuntimeError: If the repository cannot be found.
        """
        try:
            github_repository = self._github_session.get_repo(
                f"{self.config.owner}/{self.config.repository}"
            )
        except GithubException as e:
            raise RuntimeError(
                f"An error occurred while getting the repository: {str(e)}"
            )
        return github_repository

    def check_github_repo_public(self, owner: str, repo: str) -> None:
        """Checks if a GitHub repository is public.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.

        Raises:
            RuntimeError: If the repository is not public.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(url, timeout=7)

        try:
            if response.status_code == 200:
                pass
            else:
                raise RuntimeError(
                    "It is not possible to access this repository as it does not appear to be public."
                    "Access to private repositories is only possible when a token is provided. Please provide a token and try again"
                )
        except Exception as e:
            raise RuntimeError(
                f"An error occurred while checking if repository is public: {str(e)}"
            )

    def login(
        self,
    ) -> None:
        """Logs in to GitHub using the token provided in the config.

        Raises:
            RuntimeError: If the login fails.
        """
        try:
            self._github_session = Github(self.config.token)
            if self.config.token:
                user = self._github_session.get_user().login
                logger.debug(f"Logged in as {user}")
            else:
                self.check_github_repo_public(
                    self.config.owner, self.config.repository
                )
        except Exception as e:
            raise RuntimeError(f"An error occurred while logging in: {str(e)}")

    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        """Downloads files from a commit to a local directory.

        Args:
            commit: The commit to download.
            directory: The directory to download to.
            repo_sub_directory: The sub directory to download from.

        Raises:
            RuntimeError: If the repository sub directory is invalid.
        """
        contents = self.github_repo.get_contents(
            repo_sub_directory or "", ref=commit
        )
        if not isinstance(contents, List):
            raise RuntimeError("Invalid repository subdirectory.")

        os.makedirs(directory, exist_ok=True)
        tmp_symlinks: List[Tuple[str, str]] = []
        for content in contents:
            local_path = os.path.join(directory, content.name)
            if content.type == "dir":
                self.download_files(
                    commit=commit,
                    directory=local_path,
                    repo_sub_directory=content.path,
                )
            elif content.type == "symlink":
                symlink_content = self.github_repo.get_contents(
                    content.path, ref=commit
                )
                symlink_target = symlink_content.raw_data["target"]
                tmp_symlinks.append((local_path, symlink_target))
                # As it cannot be assumed at this point that the targets of the
                # symlink already exist, the symlinks are first collected here and processed later.
            else:
                try:
                    with open(local_path, "wb") as f:
                        f.write(content.decoded_content)
                except (GithubException, IOError) as e:
                    logger.error("Error processing %s: %s", content.path, e)
        for symlink in tmp_symlinks:
            symlink_source, symlink_target = symlink
            create_symlink_in_local_repo_copy(
                symlink_source=symlink_source, symlink_target=symlink_target
            )

    def get_local_context(self, path: str) -> Optional[LocalRepositoryContext]:
        """Gets the local repository context.

        Args:
            path: The path to the local repository.

        Returns:
            The local repository context.
        """
        return LocalGitRepositoryContext.at(
            path=path,
            code_repository_id=self.id,
            remote_url_validation_callback=self.check_remote_url,
        )

    def check_remote_url(self, url: str) -> bool:
        """Checks whether the remote url matches the code repository.

        Args:
            url: The remote url.

        Returns:
            Whether the remote url is correct.
        """
        https_url = f"https://{self.config.host}/{self.config.owner}/{self.config.repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(
            f".*@{self.config.host}:{self.config.owner}/{self.config.repository}.git"
        )
        if ssh_regex.fullmatch(url):
            return True

        return False


def create_symlink_in_local_repo_copy(
    symlink_source: str, symlink_target: str
) -> None:
    """This function attempts to create a symbolic link at `local_path` that points to `symlink_target`.

    If a file or directory already exists at `local_path`, it will
    be removed before the symbolic link is created.

    Args:
        symlink_source: The path where the symbolic link should be created.
        symlink_target: The path that the symbolic link should point to.

    Raises:
        FileNotFoundError: Informs that the target directory specified by
            `symlink_target` does not exist.
        PermissionError: Informs that there are insufficient permissions to
            create the symbolic link.
        NotImplementedError: Informs that symbolic links are not supported on
            the current operating system.
        OSError: Any other OS-related errors that occur.
    """
    try:
        if os.path.exists(symlink_source):
            if os.path.isdir(symlink_source):
                os.rmdir(symlink_source)
            else:
                os.remove(
                    symlink_source,
                )
        os.symlink(symlink_target, symlink_source)
    except FileNotFoundError:
        logger.warning(
            "The target directory of the symbolic link '%s' does not exist. "
            "The creation of the symbolic link is skipped.",
            symlink_target,
        )
    except PermissionError:
        logger.warning(
            "You do not have the necessary permissions to create the symbolic link. "
            "The creation of the symbolic link '%s' is skipped.",
            symlink_source,
        )
    except NotImplementedError:
        logger.warning(
            "Symbolic links are not supported on this operating system. "
            "The creation of the symbolic link '%s' is skipped.",
            symlink_source,
        )
    except OSError as e:
        logger.warning("An OS error occurred: %s", e)
