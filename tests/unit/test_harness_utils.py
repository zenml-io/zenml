"""Focused regression tests for harness session cleanup."""

import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import tests.harness.utils as harness_utils
from zenml.constants import ENV_ZENML_CONFIG_PATH


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
