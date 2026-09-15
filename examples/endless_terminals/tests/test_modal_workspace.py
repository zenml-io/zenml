"""Exercise Modal persistence boundaries without creating cloud resources."""

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from runtime.modal_workspace import ModalWorkspace
from runtime.sandbox_workspace import SandboxRuntimeConfig

from zenml.integrations.modal.flavors.modal_sandbox_flavor import (
    ModalSandboxConfig,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox


def workspace(
    monkeypatch: pytest.MonkeyPatch, sdk: Mock | None = None
) -> ModalWorkspace:
    """Build a workspace with fake canonical and Modal clients.

    Args:
        monkeypatch: Test patch fixture.
        sdk: Optional complete Modal SDK substitute.

    Returns:
        Isolated workspace fixture.
    """
    monkeypatch.setattr(
        "runtime.modal_workspace.create_modal_client_from_credentials",
        lambda **kwargs: None,
    )
    monkeypatch.setattr("runtime.modal_workspace.modal", sdk or Mock())
    sandbox = Mock(spec=ModalSandbox)
    sandbox.config = ModalSandboxConfig(
        modal_environment="dev", token_id="test-id", token_secret="test-secret"
    )
    sandbox.environment = {}
    sandbox.secrets = []
    return ModalWorkspace(
        sandbox,
        SandboxRuntimeConfig(
            helper_image="helper@sha256:" + "a" * 64,
            modal_agent_image="agent@sha256:" + "b" * 64,
        ),
    )


def test_volume_creation_checks_hydrated_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrong identity must fail before any paid or persistent allocation.

    Args:
        monkeypatch: Test patch fixture.
    """
    target = workspace(monkeypatch)
    context = Mock()
    context.hydrate.return_value = SimpleNamespace(name="personal")
    monkeypatch.setattr(
        "runtime.modal_workspace.modal.Workspace.from_context",
        Mock(return_value=context),
    )
    create = Mock()
    monkeypatch.setattr(
        "runtime.modal_workspace.modal.Volume.objects.create", create
    )
    with pytest.raises(RuntimeError, match="zenml-io"):
        target.create_volume()
    create.assert_not_called()
    context.hydrate.return_value = SimpleNamespace(name="zenml-io")
    target.create_volume()
    create.assert_called_once_with(
        target.name, environment_name="dev", client=None
    )


def test_settings_mount_only_home_and_block_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent cannot mount the image root or inject controller credentials.

    Args:
        monkeypatch: Test patch fixture.
    """
    target = workspace(monkeypatch)
    agent = target.settings("image", "/home/user")
    assert agent.block_network and agent.sandbox_environment == {}
    assert agent.gpu is None
    assert agent.volumes["/home/user"].sub_path == "/home"
    reader = target.settings("image", "/workspace", readonly=True)
    assert reader.volumes["/workspace"].read_only
    assert target.settings("image", None).volumes == {}


def test_termination_commits_before_reader_and_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reader cannot start and a Volume cannot disappear before the writer stops.

    Args:
        monkeypatch: Test patch fixture.
    """
    target = workspace(monkeypatch)
    session = Mock(id="sb-writer")
    cast(Mock, target.sandbox.create_session).return_value = session
    target.create_session("image", "/home/user")
    with pytest.raises(RuntimeError, match="preceding"):
        target.create_session("image", "/workspace", True)
    remote = Mock()
    remote.poll.return_value = None
    monkeypatch.setattr(
        "runtime.modal_workspace.modal.Sandbox.from_id",
        Mock(return_value=remote),
    )
    delete = Mock()
    monkeypatch.setattr(
        "runtime.modal_workspace.modal.Volume.objects.delete", delete
    )
    target.volume_created = True
    with pytest.raises(RuntimeError, match="cleanup incomplete"):
        target.close()
    delete.assert_not_called()
    assert session.id in target.sessions
    remote.poll.return_value = 137
    target.close()
    remote.terminate.assert_called_with(wait=True)
    session.close.assert_called_once()
    delete.assert_called_once_with(
        target.name, environment_name="dev", client=None, allow_missing=True
    )
    assert target.provenance["cleanup_complete"]


def test_component_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task containers cannot inherit any stack-injected credentials.

    Args:
        monkeypatch: Test patch fixture.
    """
    target = workspace(monkeypatch)
    target.sandbox.environment = {"TOKEN": "not-a-real-token"}
    with pytest.raises(ValueError, match="inject"):
        ModalWorkspace(target.sandbox, target.config)


def test_uncertain_volume_creation_is_cleaned_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lost create response must not silently leave this episode's volume behind.

    Args:
        monkeypatch: Test patch fixture.
    """
    sdk = Mock()
    target = workspace(monkeypatch, sdk)
    sdk.Workspace.from_context.return_value.hydrate.return_value.name = (
        "zenml-io"
    )
    sdk.Volume.objects.create.side_effect = TimeoutError("response lost")
    with pytest.raises(TimeoutError):
        target.create_volume()
    target.close()
    sdk.Volume.objects.delete.assert_called_once_with(
        target.name, environment_name="dev", client=None, allow_missing=True
    )


def test_uncertain_session_creation_preserves_volume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lost sandbox handle must never produce a successful cleanup report.

    Args:
        monkeypatch: Test patch fixture.
    """
    sdk = Mock()
    target = workspace(monkeypatch, sdk)
    target.volume_created = True
    cast(Mock, target.sandbox.create_session).side_effect = TimeoutError(
        "response lost"
    )
    with pytest.raises(TimeoutError):
        target.create_session("image", "/home/user")
    with pytest.raises(RuntimeError, match="reconciliation"):
        target.close()
    sdk.Volume.objects.delete.assert_not_called()
    assert target.provenance["session_creation_uncertain"] is True
    assert target.provenance["cleanup_complete"] is False
    with pytest.raises(RuntimeError, match="preceding"):
        target.create_session("image", "/workspace", True)


def test_trusted_seed_and_verifier_use_explicit_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Shell control operators reach a shell on every canonical backend.

    Args:
        monkeypatch: Test patch fixture.
        tmp_path: Temporary local filesystem used to replay the seed command.
    """
    import io
    import subprocess
    import tarfile

    from runtime.sandbox_env import SandboxEnvironment

    env = object.__new__(SandboxEnvironment)
    env.workspace = Mock()
    env.command_timeout = 1
    env.episode_timeout = 1
    env.shell = None
    env.agent = None
    session = Mock(id="sandbox")
    session.exec.return_value.collect.return_value = SimpleNamespace(
        exit_code=0, stdout="", stderr=""
    )
    monkeypatch.setattr(env, "_new", lambda *args, **kwargs: session)
    monkeypatch.setattr(env, "_archive", lambda *args: b"initial")
    monkeypatch.setattr("runtime.sandbox_env.SandboxShell", Mock())
    env.__enter__()
    seed_argv = session.exec.call_args.args[0]
    assert seed_argv[:2] == ["sh", "-c"]
    source = tmp_path / "source"
    source.mkdir()
    (source / "original.txt").write_text("seeded")
    volume = tmp_path / "volume"
    volume.mkdir()
    script = (
        seed_argv[2]
        .replace("/workspace", str(volume))
        .replace("/home/user", str(source))
    )
    subprocess.run([*seed_argv[:2], script], check=True)
    assert (volume / "home" / "original.txt").read_text() == "seeded"

    monkeypatch.setattr(env, "_upload", lambda *args: None)
    monkeypatch.setattr(env, "_download", lambda *args: b"<testsuite/>")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w"):
        pass
    test_path = tmp_path / "test_final_state.py"
    test_path.write_text("def test_state(): assert True\n")
    env.verify_snapshot(archive.getvalue(), test_path)
    commands = [call.args[0] for call in session.exec.call_args_list]
    assert all(command[:2] == ["sh", "-c"] for command in commands)
    assert any(
        "rm -rf /home/user && mkdir" in command[2] for command in commands
    )
    assert any(
        "cd /opt/endless-grader && python3" in command[2]
        for command in commands
    )


def test_agent_image_only_replaces_agent_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The derived image never replaces trusted seed, reader or verifier images.

    Args:
        monkeypatch: Test patch fixture.
    """
    target = workspace(monkeypatch)
    original = "original@sha256:" + "c" * 64
    assert (
        target.settings(original, "/home/user").image
        == target.config.modal_agent_image
    )
    for mount, readonly in [
        ("/workspace", False),
        ("/workspace", True),
        (None, False),
    ]:
        assert target.settings(original, mount, readonly).image == original
    cast(Mock, target.sandbox.create_session).return_value = Mock(
        id="sb-agent"
    )
    target.create_session(original, "/home/user")
    assert (
        target.provenance["sandboxes"][0]["image"]
        == target.config.modal_agent_image
    )


@pytest.mark.parametrize("image", [None, "agent:latest"])
def test_modal_agent_image_must_be_configured_and_immutable(
    monkeypatch: pytest.MonkeyPatch, image: str | None
) -> None:
    """Modal allocation requires an explicitly pinned mount-compatible image.

    Args:
        monkeypatch: Test patch fixture.
        image: Missing or mutable image reference.
    """
    from dataclasses import replace

    target = workspace(monkeypatch)
    with pytest.raises(ValueError, match="modal_agent_image"):
        ModalWorkspace(
            target.sandbox, replace(target.config, modal_agent_image=image)
        )


def test_custom_workspace_and_environment_reach_all_allocations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use configured identity for volumes, sessions, cleanup, and provenance.

    Args:
        monkeypatch: Scoped external SDK replacement.
    """
    from dataclasses import replace

    sdk = Mock()
    original = workspace(monkeypatch, sdk)
    cast(Mock, original.sandbox).config = original.sandbox.config.model_copy(
        update={"modal_environment": "research"}
    )
    target = ModalWorkspace(
        original.sandbox,
        replace(
            original.config,
            modal_workspace="external-team",
            modal_environment="research",
        ),
    )
    sdk.Workspace.from_context.return_value.hydrate.return_value.name = (
        "external-team"
    )
    target.create_volume()
    sdk.Volume.objects.create.assert_called_once_with(
        target.name, environment_name="research", client=None
    )
    assert target.settings("image", None).modal_environment == "research"
    assert target.provenance["modal_workspace"] == "external-team"
    assert target.provenance["modal_environment"] == "research"
    target.close()
    sdk.Volume.objects.delete.assert_called_once_with(
        target.name,
        environment_name="research",
        client=None,
        allow_missing=True,
    )


@pytest.mark.parametrize(
    "mismatch", ["workspace", "environment", "credentials"]
)
def test_custom_identity_mismatch_prevents_allocation(
    monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    """Reject wrong credentials or environment before persistent resources exist.

    Args:
        monkeypatch: Scoped external SDK replacement.
        mismatch: Identity check to fail.
    """
    from dataclasses import replace

    sdk = Mock()
    original = workspace(monkeypatch, sdk)
    cast(Mock, original.sandbox).config = original.sandbox.config.model_copy(
        update={
            "modal_environment": "research"
            if mismatch != "environment"
            else "other",
            "token_id": None if mismatch == "credentials" else "test-id",
        }
    )
    sdk.Workspace.from_context.return_value.hydrate.return_value.name = (
        "wrong-team"
    )
    with pytest.raises((RuntimeError, ValueError)):
        target = ModalWorkspace(
            original.sandbox,
            replace(
                original.config,
                modal_workspace="external-team",
                modal_environment="research",
            ),
        )
        target.create_volume()
    sdk.Volume.objects.create.assert_not_called()
    cast(Mock, original.sandbox.create_session).assert_not_called()
