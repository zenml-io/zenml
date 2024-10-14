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
"""GitLab code repository."""

import os
import re
from typing import Optional

from gitlab import Gitlab
from gitlab.v4.objects import Project

from zenml.code_repositories import (
    BaseCodeRepository,
    LocalRepositoryContext,
)
from zenml.code_repositories.base_code_repository import (
    BaseCodeRepositoryConfig,
)
from zenml.code_repositories.git.local_git_repository_context import (
    LocalGitRepositoryContext,
)
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)


class GitLabCodeRepositoryConfig(BaseCodeRepositoryConfig):
    """Config for GitLab code repositories.

    Args:
        url: The full URL of the GitLab project.
        group: The group of the project.
        project: The name of the GitLab project.
        host: The host of GitLab in case it is self-hosted instance.
        token: The token to access the repository.
    """

    url: Optional[str]
    group: str
    project: str
    host: Optional[str] = "gitlab.com"
    token: str = SecretField()


class GitLabCodeRepository(BaseCodeRepository):
    """GitLab code repository."""

    @property
    def config(self) -> GitLabCodeRepositoryConfig:
        """Returns the `GitLabCodeRepositoryConfig` config.

        Returns:
            The configuration.
        """
        return GitLabCodeRepositoryConfig(**self._config)

    @property
    def gitlab_project(self) -> Project:
        """The GitLab project object from the GitLab API.

        Returns:
            The GitLab project object.
        """
        return self._gitlab_session.projects.get(
            f"{self.config.group}/{self.config.project}"
        )

    def login(self) -> None:
        """Logs in to GitLab.

        Raises:
            RuntimeError: If the login fails.
        """
        try:
            self._gitlab_session = Gitlab(
                self.config.url, private_token=self.config.token
            )
            self._gitlab_session.auth()
            user = self._gitlab_session.user or None
            if user:
                logger.debug(f"Logged in as {user.username}")
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
        """
        contents = self.gitlab_project.repository_tree(
            ref=commit,
            path=repo_sub_directory or "",
        )
        for content in contents:
            logger.debug(f"Processing {content['path']}")
            if content["type"] == "tree":
                path = os.path.join(directory, content["name"])
                os.makedirs(path, exist_ok=True)
                self.download_files(
                    commit=commit,
                    directory=path,
                    repo_sub_directory=content["path"],
                )
            else:
                try:
                    path = content["path"]
                    file_content = self.gitlab_project.files.get(
                        file_path=path, ref=commit
                    ).decode()
                    path = os.path.join(directory, content["name"])
                    with open(path, "wb") as file:
                        file.write(file_content)
                except Exception as e:
                    logger.error("Error processing %s: %s", content["path"], e)

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
        https_url = f"https://{self.config.host}/{self.config.group}/{self.config.project}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(
            r"^(?P<scheme_with_delimiter>ssh://)?"
            r"(?P<userinfo>git)"
            f"@{self.config.host}:"
            r"(?P<port>\d+)?"
            r"(?(scheme_with_delimiter)/|/?)"
            f"{self.config.group}/{self.config.project}.git$",
        )
        if ssh_regex.fullmatch(url):
            return True

        return False
