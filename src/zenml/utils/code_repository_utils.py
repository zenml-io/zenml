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
"""Utilities for code repositories."""

import os
from typing import (
    Dict,
    Optional,
)

from zenml.code_repositories import (
    BaseCodeRepository,
    LocalRepositoryContext,
)
from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.pagination_utils import depaginate

logger = get_logger(__name__)


_CODE_REPOSITORY_CACHE: Dict[str, Optional["LocalRepositoryContext"]] = {}


def set_custom_local_repository(
    root: str, commit: str, repo: "BaseCodeRepository"
) -> None:
    """Manually defines a local repository for a path.

    To explain what this function does we need to take a dive into source
    resolving and what happens inside the Docker image entrypoint:
    * When trying to resolve an object to a source, we first determine whether
    the file is a user file or not.
    * If the file is a user file, we check if that user file is inside a clean
    code repository using the
    `code_repository_utils.find_active_code_repository(...)` function. If that
    is the case, the object will be resolved to a `CodeRepositorySource` which
    includes additional information about the current commit and the ID of the
    code repository.
    * The `code_repository_utils.find_active_code_repository(...)` uses the
    code repository implementation classes to check whether the code repository
    "exists" at that local path. For git repositories, this check might look as
    follows: The code repository first checks if there is a git repository at
    that path or in any parent directory. If there is, the remote URLs of this
    git repository will be checked to see if one matches the URL defined for
    the code repository.
    * When running a step inside a Docker image, ZenML potentially downloads
    files from a code repository. This usually does not download the entire
    repository (and in the case of git might not download a .git directory which
    defines a local git repository) but only specific files. If we now try to
    resolve any object while running in this container, it will not get resolved
    to a `CodeRepositorySource` as
    `code_repository_utils.find_active_code_repository(...)` won't find an
    active repository. As we downloaded these files, we however know that they
    belong to a certain code repository at a specific commit, and that's what we
    can define using this function.

    Args:
        root: The repository root.
        commit: The commit of the repository.
        repo: The code repository associated with the local repository.
    """
    from zenml.utils.downloaded_repository_context import (
        _DownloadedRepositoryContext,
    )

    global _CODE_REPOSITORY_CACHE

    path = os.path.abspath(source_utils.get_source_root())
    _CODE_REPOSITORY_CACHE[path] = _DownloadedRepositoryContext(
        code_repository_id=repo.id, root=root, commit=commit
    )


def find_active_code_repository(
    path: Optional[str] = None,
) -> Optional["LocalRepositoryContext"]:
    """Find the active code repository for a given path.

    Args:
        path: Path at which to look for the code repository. If not given, the
            source root will be used.

    Returns:
        The local repository context active at that path or None.
    """
    global _CODE_REPOSITORY_CACHE
    from zenml.client import Client
    from zenml.code_repositories import BaseCodeRepository

    path = path or source_utils.get_source_root()
    path = os.path.abspath(path)

    if path in _CODE_REPOSITORY_CACHE:
        return _CODE_REPOSITORY_CACHE[path]

    local_context: Optional["LocalRepositoryContext"] = None
    for model in depaginate(list_method=Client().list_code_repositories):
        try:
            repo = BaseCodeRepository.from_model(model)
        except Exception:
            logger.debug(
                "Failed to instantiate code repository class.", exc_info=True
            )
            continue

        local_context = repo.get_local_context(path)
        if local_context:
            break

    _CODE_REPOSITORY_CACHE[path] = local_context
    return local_context
