from dataclasses import dataclass
from typing import Any, Dict

import pytest

from zenml.integrations.gitlab.code_repositories.gitlab_code_repository import (
    GitLabCodeRepository,
)

CONFIG_I = {
    "url": "https://gitlab.com",
    "host": "gitlab.com",
    "group": "example",
    "project": "test",
}

CONFIG_II = {
    "url": "https://private-gitlab.example.com",
    "host": "private-gitlab.example.com",
    "group": "example",
    "project": "test",
}


@dataclass
class DummyGitLabCodeRepositoryConfig:
    url: str
    group: str
    project: str
    host: str


class DummyGitLabCodeRepository(GitLabCodeRepository):
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config

    @property
    def config(self) -> DummyGitLabCodeRepositoryConfig:
        return DummyGitLabCodeRepositoryConfig(**self._config)


@pytest.mark.parametrize(
    ("config", "url", "expected"),
    [
        (CONFIG_I, "git@gitlab.com:example/test.git", True),
        (CONFIG_I, "git@gitlab.com:/example/test.git", True),
        (CONFIG_I, "ssh://git@gitlab.com:example/test.git", False),
        (CONFIG_I, "ssh://git@gitlab.com:/example/test.git", True),
        (CONFIG_I, "ssh://git@gitlab.com:22/example/test.git", True),
        (
            CONFIG_II,
            "ssh://git@private-gitlab.example.com:2222/example/test.git",
            True,
        ),
        (
            CONFIG_II,
            "https://private-gitlab.example.com/example/test.git",
            True,
        ),
        (
            CONFIG_II,
            "https://private-gitlab.example.invalid/example/test.git",
            False,
        ),
        (
            CONFIG_II,
            "https://private-gitlab.example.com/invalid/test.git",
            False,
        ),
        (
            CONFIG_II,
            "https://private-gitlab.example.com/example/invalid.git",
            False,
        ),
        (
            CONFIG_II,
            "https://private-gitlab.example.com/example/test.invalid",
            False,
        ),
    ],
)
def test_check_remote_url(
    config: Dict[str, Any],
    url: str,
    expected: Any,
) -> None:
    cr = DummyGitLabCodeRepository(config)
    assert cr.check_remote_url(url) == expected
