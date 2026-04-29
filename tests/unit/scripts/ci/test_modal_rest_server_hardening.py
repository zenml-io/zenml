"""Regression tests for Modal REST server CI hardening."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts.ci import provision_modal_server
from tests.harness.deployment import _modal_runtime
from tests.harness.deployment.server_modal_mysql import (
    ENV_MODAL_SERVER_PASSWORD,
    ENV_MODAL_SERVER_URL,
    ENV_MODAL_SERVER_USERNAME,
    ServerModalMySQLTestDeployment,
)
from tests.harness.model import DeploymentConfig

from zenml.constants import (
    ENV_ZENML_DEFAULT_USER_NAME,
    ENV_ZENML_DEFAULT_USER_PASSWORD,
)


class _FakeImage:
    """Minimal Modal image double that records context operations."""

    operations: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    @classmethod
    def from_registry(cls, *args: Any, **kwargs: Any) -> "_FakeImage":
        cls.operations = [("from_registry", args, kwargs)]
        return cls()

    def add_local_file(self, *args: Any, **kwargs: Any) -> "_FakeImage":
        self.operations.append(("add_local_file", args, kwargs))
        return self

    def add_local_dir(self, *args: Any, **kwargs: Any) -> "_FakeImage":
        self.operations.append(("add_local_dir", args, kwargs))
        return self

    def run_commands(self, *args: Any, **kwargs: Any) -> "_FakeImage":
        self.operations.append(("run_commands", args, kwargs))
        return self

    def env(self, *args: Any, **kwargs: Any) -> "_FakeImage":
        self.operations.append(("env", args, kwargs))
        return self


def _deployment() -> ServerModalMySQLTestDeployment:
    return ServerModalMySQLTestDeployment(
        DeploymentConfig(name="modal-server-mysql")
    )


def test_server_image_context_uses_allowlist(monkeypatch: Any) -> None:
    """Keeps sensitive checkout paths out of the Modal server image."""
    fake_modal = SimpleNamespace(Image=_FakeImage)
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    _modal_runtime.build_server_image(
        db_image="mysql:8.0",
        python_version="3.11",
        db_env={"MYSQL_DATABASE": "zenml"},
    )

    local_files = {
        Path(args[0]).relative_to(_modal_runtime.REPO_ROOT).as_posix()
        for operation, args, _ in _FakeImage.operations
        if operation == "add_local_file" and args[1].startswith("/src/zenml/")
    }
    local_dirs = {
        Path(args[0]).relative_to(_modal_runtime.REPO_ROOT).as_posix()
        for operation, args, _ in _FakeImage.operations
        if operation == "add_local_dir"
    }

    assert local_files == set(
        _modal_runtime.ALLOWLISTED_SERVER_IMAGE_CONTEXT_FILES
    )
    assert local_dirs == set(
        _modal_runtime.ALLOWLISTED_SERVER_IMAGE_CONTEXT_DIRS
    )
    assert "tests" not in local_dirs
    assert "examples" not in local_dirs
    assert "prompt-exports" not in local_dirs
    assert all(
        "ignore" not in kwargs for _, _, kwargs in _FakeImage.operations
    )


def test_stop_modal_app_uses_selected_environment(monkeypatch: Any) -> None:
    """Shares app cleanup through the runtime helper."""
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setenv("MODAL_ENVIRONMENT", "ci")
    monkeypatch.setattr(_modal_runtime.shutil, "which", lambda _: "/bin/modal")
    monkeypatch.setattr(_modal_runtime.subprocess, "run", fake_run)

    assert _modal_runtime.stop_modal_app("zenml-test-app") is True
    assert calls == [
        ["/bin/modal", "app", "stop", "zenml-test-app", "--env", "ci"]
    ]


def test_preprovisioned_server_store_config_uses_env_credentials(
    monkeypatch: Any,
) -> None:
    """Connects offloaded tests with the generated per-run credentials."""
    monkeypatch.setenv(ENV_MODAL_SERVER_URL, "https://example.modal.run")
    monkeypatch.setenv(ENV_MODAL_SERVER_USERNAME, "ci_user")
    monkeypatch.setenv(ENV_MODAL_SERVER_PASSWORD, "ci_password")

    store_config = _deployment().get_store_config()

    assert store_config is not None
    assert store_config.url == "https://example.modal.run"
    assert store_config.username == "ci_user"
    assert store_config.password == "ci_password"


def test_modal_server_sandbox_receives_credentials_as_secret(
    monkeypatch: Any,
) -> None:
    """Avoids baking REST credentials into the image or logging them."""
    created_secrets: list[dict[str, str]] = []
    create_kwargs: dict[str, Any] = {}

    class FakeSecret:
        @staticmethod
        def from_dict(values: dict[str, str]) -> dict[str, str]:
            created_secrets.append(values)
            return values

    class FakeApp:
        @staticmethod
        def lookup(*_: Any, **__: Any) -> object:
            return object()

    class FakeSandbox:
        object_id = "sb-123"

        @staticmethod
        def create(*_: Any, **kwargs: Any) -> "FakeSandbox":
            create_kwargs.update(kwargs)
            return FakeSandbox()

        def poll(self) -> None:
            return None

        def tunnels(self) -> dict[int, SimpleNamespace]:
            return {
                _modal_runtime.ZENML_SERVER_PORT: SimpleNamespace(
                    url="https://server.modal.run"
                )
            }

        def terminate(self) -> None:
            pass

    fake_modal = SimpleNamespace(
        App=FakeApp,
        Sandbox=FakeSandbox,
        Secret=FakeSecret,
    )
    monkeypatch.setitem(sys.modules, "modal", fake_modal)
    monkeypatch.setenv("MODAL_TOKEN_ID", "token-id")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "token-secret")
    monkeypatch.setenv(ENV_MODAL_SERVER_USERNAME, "ci_user")
    monkeypatch.setenv(ENV_MODAL_SERVER_PASSWORD, "ci_password")
    monkeypatch.setattr(
        "tests.harness.deployment.server_modal_mysql.build_server_image",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        "tests.harness.deployment.server_modal_mysql.wait_for_server",
        lambda _: None,
    )

    deployment = _deployment()
    deployment.up()

    assert created_secrets == [
        {
            ENV_ZENML_DEFAULT_USER_NAME: "ci_user",
            ENV_ZENML_DEFAULT_USER_PASSWORD: "ci_password",
        }
    ]
    assert create_kwargs["secrets"] == created_secrets

    monkeypatch.setenv(ENV_MODAL_SERVER_USERNAME, "changed_user")
    monkeypatch.setenv(ENV_MODAL_SERVER_PASSWORD, "changed_password")
    assert deployment.get_store_config().username == "ci_user"
    assert deployment.get_store_config().password == "ci_password"


def test_provision_generates_masks_and_outputs_credentials(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    """Provisioning emits credentials through GitHub outputs, not logs."""

    class EnableOutput:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_: Any) -> None:
            return None

    class FakeDeployment:
        sandbox_id = "sb-123"
        app_name = "zenml-test-app"

        def up(self) -> None:
            assert os_environ[ENV_MODAL_SERVER_USERNAME] == "ci_abcdef123456"
            assert (
                os_environ[ENV_MODAL_SERVER_PASSWORD] == "generated-password"
            )

        def get_store_config(self) -> SimpleNamespace:
            return SimpleNamespace(url="https://server.modal.run")

    os_environ = provision_modal_server.os.environ
    output_path = tmp_path / "github-output.txt"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setitem(
        sys.modules,
        "modal",
        SimpleNamespace(enable_output=lambda: EnableOutput()),
    )
    monkeypatch.setattr(
        provision_modal_server,
        "_get_modal_deployment",
        lambda _: FakeDeployment(),
    )
    monkeypatch.setattr(
        provision_modal_server.secrets,
        "token_hex",
        lambda _: "abcdef123456",
    )
    monkeypatch.setattr(
        provision_modal_server.secrets,
        "token_urlsafe",
        lambda _: "generated-password",
    )

    assert provision_modal_server.provision("modal-server-mysql") == 0

    stdout = capsys.readouterr().out
    assert "server_password=<written to GITHUB_OUTPUT>" in stdout
    assert "server_password=generated-password" not in stdout
    assert "::add-mask::ci_abcdef123456" in stdout
    assert "::add-mask::generated-password" in stdout
    assert output_path.read_text() == (
        "server_url=https://server.modal.run\n"
        "server_username=ci_abcdef123456\n"
        "server_password=generated-password\n"
        "sandbox_id=sb-123\n"
        "app_name=zenml-test-app\n"
    )
