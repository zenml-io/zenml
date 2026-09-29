"""Persist only task home data between isolated canonical Modal sessions."""

from __future__ import annotations

import re
import uuid
from typing import Any

import modal
from modal.exception import AlreadyExistsError

from zenml.integrations.modal.flavors.modal_sandbox_flavor import (
    ModalSandboxSettings,
    ModalSandboxVolumeMount,
)
from zenml.integrations.modal.sandbox_utils import (
    create_modal_client_from_credentials,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox
from zenml.sandboxes.session import SandboxSession

from .sandbox_workspace import SandboxRuntimeConfig, bounded_call


class ModalWorkspace:
    """Use a unique Volume without copying or trusting the agent filesystem."""

    def __init__(
        self, sandbox: ModalSandbox, config: SandboxRuntimeConfig
    ) -> None:
        """Configure the workspace without allocating resources.

        Args:
            sandbox: Active canonical Modal sandbox component.
            config: Bounded bootstrap and cleanup settings.

        Raises:
            ValueError: The component would inject credentials or targets another environment.
        """
        if sandbox.config.modal_environment != config.modal_environment:
            raise ValueError(
                f"Task sandbox must target Modal environment {config.modal_environment}"
            )
        if (
            sandbox.config.sandbox_environment
            or sandbox.environment
            or sandbox.secrets
        ):
            raise ValueError(
                "Task sandbox must not inject environment values or secrets"
            )
        if not re.fullmatch(
            r"[^\s]+@sha256:[0-9a-f]{64}", config.helper_image
        ):
            raise ValueError(
                "Helper image must use an immutable registry digest"
            )
        if (
            min(
                config.startup_timeout,
                config.cleanup_timeout,
                config.api_timeout,
            )
            <= 0
        ):
            raise ValueError("Workspace timeouts must be positive")
        if not config.modal_agent_image or not re.fullmatch(
            r"[^\s@]+@sha256:[0-9a-f]{64}", config.modal_agent_image
        ):
            raise ValueError(
                "Modal requires modal_agent_image pinned by registry digest "
                "with an empty /home/user mount point"
            )
        self.agent_image = config.modal_agent_image
        self.sandbox = sandbox
        self.config = config
        if not sandbox.config.token_id or not sandbox.config.token_secret:
            raise ValueError(
                "Task sandbox requires explicit Modal credentials"
            )
        self.client = create_modal_client_from_credentials(
            token_id=sandbox.config.token_id,
            token_secret=sandbox.config.token_secret,
        )
        self.name = "endless-workspace-" + uuid.uuid4().hex
        self.volume_created = False
        self.volume_attempted = False
        self.session_creation_uncertain = False
        self.sessions: dict[str, SandboxSession] = {}
        self.provenance: dict[str, Any] = {
            "backend": "modal_sandbox",
            "modal_workspace": config.modal_workspace,
            "modal_environment": config.modal_environment,
            "workspace_name": self.name,
            "sandboxes": [],
            "cleanup_complete": False,
        }

    def create_volume(self) -> None:
        """Verify workspace identity before creating this episode's named Volume.

        Raises:
            RuntimeError: Modal credentials select another workspace.
            AlreadyExistsError: The generated Volume name already exists.
        """
        workspace = bounded_call(
            lambda: modal.Workspace.from_context(client=self.client).hydrate(),
            self.config.api_timeout,
        )
        if workspace.name != self.config.modal_workspace:
            raise RuntimeError(
                f"Modal credentials must select workspace {self.config.modal_workspace}"
            )
        # Creation is deliberately synchronous: no abandoned daemon may create a
        # volume after cleanup has already checked for it.
        self.volume_attempted = True
        try:
            modal.Volume.objects.create(
                self.name,
                environment_name=self.config.modal_environment,
                client=self.client,
            )
        except AlreadyExistsError:
            self.volume_attempted = False
            raise
        self.volume_created = True

    def settings(
        self, image: str, mount: str | None, readonly: bool = False
    ) -> ModalSandboxSettings:
        """Request isolated CPU sessions with only the named home data mounted.

        Args:
            image: Immutable task image.
            mount: Workspace root, agent home, or no volume for a verifier.
            readonly: Whether the mounted Volume must reject writes.

        Returns:
            Canonical Modal sandbox settings.
        """
        volumes = {}
        if mount:
            volumes[mount] = ModalSandboxVolumeMount(
                name=self.name,
                sub_path="/home" if mount == "/home/user" else None,
                read_only=readonly,
            )
        return ModalSandboxSettings(
            image=self.agent_image if mount == "/home/user" else image,
            modal_environment=self.config.modal_environment,
            cpu=1,
            memory="1GiB",
            gpu=None,
            timeout=1800,
            block_network=True,
            sandbox_environment={},
            volumes=volumes,
        )

    def create_session(
        self, image: str, mount: str | None, readonly: bool = False
    ) -> SandboxSession:
        """Create and record a canonical session before running any commands.

        Args:
            image: Immutable task image.
            mount: Optional data volume mount point.
            readonly: Whether the data volume is read-only.

        Returns:
            Running canonical sandbox session.

        Raises:
            RuntimeError: A preceding writer remains active.
        """
        if self.sessions or self.session_creation_uncertain:
            raise RuntimeError(
                "Terminate the preceding Modal session before creating another"
            )
        settings = self.settings(image, mount, readonly)
        self.session_creation_uncertain = True
        self.provenance["session_creation_uncertain"] = True
        session = self.sandbox.create_session(settings=settings)
        self.sessions[session.id] = session
        self.session_creation_uncertain = False
        self.provenance["session_creation_uncertain"] = False
        self.provenance["sandboxes"].append(
            {
                "session_id": session.id,
                "image": settings.image,
                "network_blocked": True,
                "phase": "agent"
                if mount == "/home/user"
                else "reader"
                if readonly
                else "seed"
                if mount
                else "verifier",
            }
        )
        return session

    def destroy_session(self, session: SandboxSession) -> None:
        """Confirm termination and the backend's final Volume commit before reading.

        Modal documents a final commit on Sandbox termination. This uses the
        server API, never sync or archive code from the agent container.

        Args:
            session: Owned canonical session.

        Raises:
            RuntimeError: Termination was not confirmed.
        """
        if session.id not in self.sessions:
            return
        remote = modal.Sandbox.from_id(session.id, client=self.client)
        bounded_call(
            lambda: remote.terminate(wait=True), self.config.cleanup_timeout
        )
        if bounded_call(remote.poll, self.config.api_timeout) is None:
            raise RuntimeError("Modal sandbox termination was not confirmed")
        session.close()
        del self.sessions[session.id]
        self.provenance.setdefault("terminated_sandbox_ids", []).append(
            session.id
        )

    def close(self) -> None:
        """Delete the episode Volume only after all owned sessions have terminated.

        Raises:
            RuntimeError: A session could not be terminated.
        """
        errors = []
        if self.session_creation_uncertain:
            errors.append(
                "Sandbox creation did not return an ID; a sandbox may still "
                "exist and requires reconciliation before deleting the Volume"
            )
        for session in list(self.sessions.values()):
            try:
                self.destroy_session(session)
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError(
                "Modal workspace cleanup incomplete: " + "; ".join(errors)
            )
        if self.volume_attempted or self.volume_created:
            modal.Volume.objects.delete(
                self.name,
                environment_name=self.config.modal_environment,
                client=self.client,
                allow_missing=True,
            )
            self.volume_created = False
            self.volume_attempted = False
        self.provenance["cleanup_complete"] = True
