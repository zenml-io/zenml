"""Focused regression tests for harness session cleanup."""

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Generator
from uuid import UUID, uuid4

import pytest

import tests.harness.utils as harness_utils
from zenml.constants import DEFAULT_PROJECT_NAME, ENV_ZENML_CONFIG_PATH


class _DummyTmpPathFactory:
    """Minimal stand-in for `pytest.TempPathFactory`."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def mktemp(self, prefix: str) -> Path:
        path = self._root / prefix
        path.mkdir(parents=True)
        return path


def test_clean_default_client_session_rewrites_template_paths_and_restores_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Tests that template copies stay isolated and env vars are restored."""
    template_dir = tmp_path / "template"
    template_zenml = template_dir / "zenml"
    template_zenml.mkdir(parents=True)

    template_root = template_dir.resolve()
    session_root = tmp_path / "clean-client-session"
    session_factory = _DummyTmpPathFactory(session_root)
    client_root = session_root / "pytest-clean-client"

    (template_zenml / "config.yaml").write_text(
        "database: {root}/zenml.db\nbackup_directory: {root}/backup\n".format(
            root=template_root
        )
    )

    monkeypatch.setenv(ENV_ZENML_CONFIG_PATH, "original-config-path")
    monkeypatch.setenv("DISABLE_DATABASE_MIGRATION", "sentinel")

    clear_calls = {"count": 0}
    stack_module = ModuleType("zenml.stack.stack")
    stack_module._STACK_CACHE = SimpleNamespace(
        clear=lambda: clear_calls.__setitem__(
            "count", clear_calls["count"] + 1
        )
    )
    monkeypatch.setitem(sys.modules, "zenml.stack.stack", stack_module)

    class FakeGlobalConfiguration:
        def __init__(self) -> None:
            self.analytics_opt_in = True

        @classmethod
        def get_instance(cls) -> object:
            return object()

        @classmethod
        def _reset_instance(cls, instance: object | None = None) -> None:
            del instance

    class FakeClient:
        def __init__(self) -> None:
            self.zen_store = SimpleNamespace()

        @classmethod
        def get_instance(cls) -> object:
            return object()

        @classmethod
        def _reset_instance(cls, instance: object | None = None) -> None:
            del instance

    class FakeCredentialsStore:
        @classmethod
        def get_instance(cls) -> object:
            return object()

        @classmethod
        def reset_instance(cls, instance: object | None = None) -> None:
            del instance

    monkeypatch.setattr(
        harness_utils, "GlobalConfiguration", FakeGlobalConfiguration
    )
    monkeypatch.setattr(harness_utils, "Client", FakeClient)
    monkeypatch.setattr(
        harness_utils, "CredentialsStore", FakeCredentialsStore
    )

    with harness_utils.clean_default_client_session(
        tmp_path_factory=session_factory,
        template_dir=template_dir,
    ) as client:
        assert isinstance(client, FakeClient)
        assert clear_calls["count"] == 1
        assert Path(os.environ[ENV_ZENML_CONFIG_PATH]) == client_root / "zenml"
        assert os.getenv("DISABLE_DATABASE_MIGRATION") == "sentinel"

        rewritten_config = (client_root / "zenml" / "config.yaml").read_text()
        assert str(template_root) not in rewritten_config
        assert str(client_root.resolve()) in rewritten_config

    assert os.getenv(ENV_ZENML_CONFIG_PATH) == "original-config-path"
    assert os.getenv("DISABLE_DATABASE_MIGRATION") == "sentinel"


def test_no_provision_isolated_session_restores_default_active_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests project isolation when a reused server has no local active project."""

    class FakeClient:
        def __init__(self) -> None:
            self.default_project_id = uuid4()
            self.projects = {
                self.default_project_id: SimpleNamespace(
                    id=self.default_project_id,
                    name=DEFAULT_PROJECT_NAME,
                )
            }
            self.active_project_id: UUID | None = None
            self.deleted_projects: list[str] = []
            self.set_active_calls: list[str | UUID] = []

        @property
        def active_project(self) -> SimpleNamespace:
            if self.active_project_id is None:
                raise RuntimeError("No project is currently set as active.")
            return self.projects[self.active_project_id]

        def set_active_project(
            self, project_name_or_id: str | UUID
        ) -> SimpleNamespace:
            self.set_active_calls.append(project_name_or_id)
            for project in self.projects.values():
                if (
                    project.id == project_name_or_id
                    or project.name == project_name_or_id
                ):
                    self.active_project_id = project.id
                    return project
            raise KeyError(project_name_or_id)

        def create_project(
            self, name: str, description: str
        ) -> SimpleNamespace:
            del description
            project_id = uuid4()
            project = SimpleNamespace(id=project_id, name=name)
            self.projects[project_id] = project
            return project

        def delete_project(self, project_name_or_id: str | UUID) -> None:
            self.deleted_projects.append(str(project_name_or_id))
            for project_id, project in list(self.projects.items()):
                if (
                    project.id == project_name_or_id
                    or project.name == project_name_or_id
                ):
                    del self.projects[project_id]
                    return
            raise KeyError(project_name_or_id)

    class FakeDeployment:
        def __init__(self, client: FakeClient) -> None:
            self._client = client

        @contextmanager
        def connect(self) -> Generator[FakeClient, None, None]:
            yield self._client

    client = FakeClient()
    environment = SimpleNamespace(deployment=FakeDeployment(client))

    class FakeTestHarness:
        def set_environment(self, **kwargs: object) -> SimpleNamespace:
            del kwargs
            return environment

    monkeypatch.setattr(harness_utils, "TestHarness", FakeTestHarness)
    monkeypatch.setenv("ZENML_TEST_ISOLATE_PROJECT", "true")

    with harness_utils.environment_session(no_provision=True) as (
        yielded_environment,
        yielded_client,
    ):
        assert yielded_environment is environment
        assert yielded_client is client
        assert client.set_active_calls[0] == DEFAULT_PROJECT_NAME
        isolated_project_name = client.active_project.name
        assert isolated_project_name.startswith("pytest_")

    assert client.active_project.id == client.default_project_id
    assert client.set_active_calls[-1] == client.default_project_id
    assert client.deleted_projects == [isolated_project_name]
