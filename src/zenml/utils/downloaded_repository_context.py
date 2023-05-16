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
"""Downloaded code repository."""
from uuid import UUID

from zenml.code_repositories import LocalRepositoryContext


class _DownloadedRepositoryContext(LocalRepositoryContext):
    """Class that represents the downloaded files of a code repository.

    See `code_repository_utils.set_custom_local_repository(...)` for a more
    in-depth explanation.
    """

    def __init__(
        self,
        code_repository_id: UUID,
        root: str,
        commit: str,
    ):
        super().__init__(code_repository_id=code_repository_id)
        self._root = root
        self._commit = commit

    @property
    def root(self) -> str:
        return self._root

    @property
    def is_dirty(self) -> bool:
        return False

    @property
    def has_local_changes(self) -> bool:
        return False

    @property
    def current_commit(self) -> str:
        return self._commit
