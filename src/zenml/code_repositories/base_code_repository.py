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
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, cast

from git.exc import InvalidGitRepositoryError
from git.repo.base import Repo
from github import Github
from pydantic import BaseModel
from zenml.exceptions import CodeRepoDownloadError

from zenml.logger import get_logger

logger = get_logger(__name__)


class BaseCodeRepository(BaseModel, ABC):
    @classmethod
    @abstractmethod
    def exists_at_path(cls, path: str, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def is_active(self, path: str) -> bool:
        # whether path is inside the locally checked out repo
        pass

    @property
    @abstractmethod
    def root(self) -> str:
        pass

    @property
    @abstractmethod
    def is_dirty(self) -> bool:
        # uncommited changes
        pass

    @property
    @abstractmethod
    def has_local_changes(self) -> bool:
        # uncommited or unpushed changes
        pass

    @property
    @abstractmethod
    def current_commit(self) -> str:
        pass

    @abstractmethod
    def download_files(self, commit: str, directory: str) -> None:
        # download files of commit to local directory
        pass


class _GitCodeRepository(BaseCodeRepository, ABC):
    @property
    def git_repo(self) -> Repo:
        return Repo(search_parent_directories=True)

    @property
    def root(self) -> str:
        assert self.git_repo.working_dir
        return str(self.git_repo.working_dir)

    @property
    def is_dirty(self) -> bool:
        return self.git_repo.is_dirty(untracked_files=True)

    @property
    def has_local_changes(self) -> bool:
        if self.is_dirty:
            return True

        remote = self.git_repo.remote(name="origin")  # make this configurable?
        remote.fetch()

        local_commit = self.git_repo.head.commit
        remote_commit = remote.refs[self.git_repo.active_branch].commit

        return remote_commit != local_commit

    @property
    def current_commit(self) -> str:
        return cast(str, self.git_repo.head.object.hexsha)

    @classmethod
    def exists_at_path(cls, path: str, config: Dict[str, Any]) -> bool:
        try:
            repo = Repo(path=path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return False

        for remote in repo.remotes:
            if cls.url_matches_config(url=remote.url, config=config):
                return True

        return False

    @classmethod
    @abstractmethod
    def url_matches_config(cls, url: str, config: Dict[str, Any]) -> bool:
        pass


class GitHubCodeRepository(_GitCodeRepository):

    def login(self, config: Dict[str, Any]) -> None:
        owner = config["owner"]
        repository = config["repository"]
        token = config["token"]
        try:
            user = self.g.get_user().login
            print(f'Logged in as {user}')
        except Exception as e:
            print(f'Error: {str(e)}')
        self.g = Github(token)
        self.repo = self.g.get_repo(f"{owner}/{repository}")

    def download_files(self, commit: str, directory: str) -> None:
        try:
            contents = self.repo.get_contents("", ref=commit)
            for content_file in contents:
                if content_file.type == "file":
                    file_contents = content_file.decoded_content
                    file_path = f'{directory}/{content_file.path}'
                    with open(file_path, "wb") as f:
                        f.write(file_contents)
            logger.info(f'Successfully downloaded files for commit {commit} to directory {directory}')
        except Exception as e:
            raise CodeRepoDownloadError(f'f"An error occurred while downloading files: {str(e)}')

    @classmethod
    def url_matches_config(cls, url: str, config: Dict[str, Any]) -> bool:
        owner = config["owner"]
        repository = config["repository"]

        https_url = f"https://github.com/{owner}/{repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(f".*@github.com:{owner}/{repository}.git")

        if ssh_regex.fullmatch(url):
            return True

        return False
