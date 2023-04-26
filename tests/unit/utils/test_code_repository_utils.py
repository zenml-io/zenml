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

import pathlib

from tests.unit.pipelines.test_build_utils import (
    StubCodeRepository,
    StubLocalRepositoryContext,
)
from zenml.models import Page
from zenml.utils import code_repository_utils

CURRENT_MODULE_PARENT_DIR = str(pathlib.Path(__file__).resolve().parent)


def test_finding_active_code_repo(mocker, sample_code_repo_response_model):
    """Tests finding the active code repo for a path."""
    code_repository_utils._CODE_REPOSITORY_CACHE = {}
    mock_list_repos = mocker.patch(
        "zenml.client.Client.list_code_repositories",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )
    assert not code_repository_utils.find_active_code_repository()
    mock_list_repos.assert_called()

    mock_list_repos = mocker.patch(
        "zenml.client.Client.list_code_repositories",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=1,
            items=[sample_code_repo_response_model],
        ),
    )

    # Don't fail if the `from_model` method fails
    mocker.patch(
        "zenml.code_repositories.BaseCodeRepository.from_model",
        side_effect=ImportError,
    )
    code_repository_utils._CODE_REPOSITORY_CACHE = {}
    assert not code_repository_utils.find_active_code_repository()

    repo_without_local = StubCodeRepository(local_context=None)
    mocker.patch(
        "zenml.code_repositories.BaseCodeRepository.from_model",
        return_value=repo_without_local,
    )

    code_repository_utils._CODE_REPOSITORY_CACHE = {}
    assert not code_repository_utils.find_active_code_repository()

    local_context = StubLocalRepositoryContext()
    repo_with_local = StubCodeRepository(local_context=local_context)
    mocker.patch(
        "zenml.code_repositories.BaseCodeRepository.from_model",
        return_value=repo_with_local,
    )
    code_repository_utils._CODE_REPOSITORY_CACHE = {}
    assert code_repository_utils.find_active_code_repository() is local_context

    # Cleanup
    code_repository_utils._CODE_REPOSITORY_CACHE = {}


def test_setting_a_custom_active_code_repo(mocker):
    """Tests setting and getting a custom local repo."""
    mock_list_repos = mocker.patch(
        "zenml.client.Client.list_code_repositories",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )

    code_repository_utils._CODE_REPOSITORY_CACHE = {}

    repo = StubCodeRepository()
    code_repository_utils.set_custom_local_repository(
        root=".", commit="commit", repo=repo
    )
    local_repo = code_repository_utils.find_active_code_repository()
    assert local_repo.code_repository_id == repo.id
    assert local_repo.root == "."
    assert local_repo.current_commit == "commit"

    mock_list_repos.assert_not_called()

    # Cleanup
    code_repository_utils._CODE_REPOSITORY_CACHE = {}
