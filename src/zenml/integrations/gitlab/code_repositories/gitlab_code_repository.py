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
import os
import re
from typing import Optional
from uuid import UUID

from gitlab import Gitlab
from gitlab.v4.objects import Repository

from zenml.code_repositories import (
    BaseCodeRepository,
    LocalRepository,
)
from zenml.code_repositories.git.local_git_repository import LocalGitRepository
from zenml.logger import get_logger

logger = get_logger(__name__)


class GitLabCodeRepository(BaseCodeRepository):
    """GitLab code repository."""

    def __init__(
        self, id: UUID, owner: str, repository: str, token: str, base_url: str
    ):
        """Initializes a GitLab code repository.

        Args:
            id: The id of the code repository.
            owner: The owner of the repository.
            repository: The name of the repository.
            token: The GitLab token.
            base_url: The base url of the GitLab instance.
        """
        super().__init__(id=id)
        self._owner = owner
        self._repository = repository
        self._token = token
        self._base_url = base_url
        self.login()

    @property
    def gitlab_repo(self) -> Repository:
        """The GitLab repository."""
        return self._gitlab_project.repository

    def login(self) -> None:
        """Logs in to GitLab."""
        try:
            self._gitlab_session = Gitlab(
                self._base_url, private_token=self._token
            )
            self._gitlab_project = self._gitlab_session.projects.get(
                f"{self._owner}/{self._repository}"
            )
            user = self._gitlab_session.user.username
            logger.debug(f"Logged in as {user}")
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
        contents = self.gitlab_repo.tree(
            ref=commit,
            path=repo_sub_directory or "",
        )
        for content in contents:
            logger.debug(f"Processing {content.path}")
            if content.type == "tree":
                path = os.path.join(directory, content.name)
                os.makedirs(path, exist_ok=True)
                self.download_files(
                    commit=commit,
                    directory=path,
                    repo_sub_directory=content.path,
                )
            else:
                try:
                    path = content.path
                    content_file = self.gitlab_repo.files.get(
                        file_path=path, ref=commit
                    )
                    data = content_file.decode().encode()
                    path = os.path.join(directory, content.name)
                    with open(path, "wb") as file:
                        file.write(data)
                except Exception as e:
                    logger.error("Error processing %s: %s", content.path, e)

    def get_local_repo(self, path: str) -> Optional[LocalRepository]:
        """Gets the local repository.

        Args:
            path: The path to the local repository.

        Returns:
            The local repository.
        """
        return LocalGitRepository.at(
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
        https_url = f"{self._base_url}/{self._owner}/{self._repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(
            f".*@{self._base_url}:{self._owner}/{self._repository}.git"
        )
        if ssh_regex.fullmatch(url):
            return True

        return False
