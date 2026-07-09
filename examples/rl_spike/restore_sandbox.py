"""Restore a failed episode's sandbox snapshot and look around inside it.

Counterpart to `run_episode(..., snapshot_on_failure=True)`: the episode
record carries a `snapshot` dict (flavor ref + sandbox component id), and
this script turns that back into a live session you can poke at — the
one-click answer to "what did the sandbox look like when this rollout
failed?" (BREAKAGE_LOG entry 16 is the incident that motivated it).

Usage:
    # From the failed episode's output artifact (the normal path):
    python restore_sandbox.py <episode-artifact-version-id>

    # From a raw snapshot reference:
    python restore_sandbox.py --ref <ref> --sandbox-id <component-uuid>

    # One-shot command instead of the interactive prompt:
    python restore_sandbox.py <artifact-id> --command "ls -la"

Only the Modal sandbox flavor implements snapshot/restore today; on any
other flavor the episode record contains `snapshot_error` instead of a
snapshot and this script tells you so.
"""

import argparse
import sys
from typing import Optional
from uuid import UUID

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.sandboxes import BaseSandbox, SandboxSnapshot
from zenml.stack import StackComponent


def _snapshot_from_artifact(artifact_version_id: str) -> SandboxSnapshot:
    """Load the snapshot reference from a failed episode's output artifact.

    Args:
        artifact_version_id: UUID of the episode dict artifact version.

    Returns:
        The parsed snapshot reference.
    """
    episode = Client().get_artifact_version(UUID(artifact_version_id)).load()
    if not isinstance(episode, dict):
        sys.exit(
            f"Artifact {artifact_version_id} is not an episode dict "
            f"(got {type(episode).__name__})."
        )
    if episode.get("snapshot_error"):
        sys.exit(
            "This episode could not snapshot its sandbox: "
            f"{episode['snapshot_error']}\n"
            "(Only the Modal sandbox flavor supports snapshots today.)"
        )
    snapshot = episode.get("snapshot")
    if not snapshot:
        sys.exit(
            "This episode carries no snapshot. Either it did not fail, or "
            "the run was launched without --snapshot-on-failure."
        )
    return SandboxSnapshot(**snapshot)


def _load_sandbox(sandbox_id: UUID) -> BaseSandbox:
    """Instantiate the exact sandbox component that produced the snapshot.

    Restore validates `snapshot.sandbox_id` against the component's own id,
    so we fetch by that id rather than trusting the active stack.

    Args:
        sandbox_id: UUID of the sandbox stack component.

    Returns:
        The instantiated sandbox component.
    """
    model = Client().get_stack_component(
        component_type=StackComponentType.SANDBOX,
        name_id_or_prefix=sandbox_id,
    )
    component = StackComponent.from_model(model)
    assert isinstance(component, BaseSandbox)
    return component


def _run_command(session: object, command: str) -> int:
    """Run one shell command in the restored session and print its output.

    Args:
        session: The restored sandbox session.
        command: Shell command line.

    Returns:
        The command's exit code.
    """
    process = session.exec(["sh", "-c", command])  # type: ignore[attr-defined]
    output = process.collect()
    if output.stdout:
        print(output.stdout, end="")
    if output.stderr:
        print(output.stderr, end="", file=sys.stderr)
    return int(output.exit_code)


def main() -> None:
    """Restore a snapshot and open an exec prompt (or run one command)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifact",
        nargs="?",
        help="Episode output artifact version id carrying the snapshot",
    )
    parser.add_argument("--ref", help="Raw flavor-specific snapshot ref")
    parser.add_argument(
        "--sandbox-id",
        help="Sandbox component UUID (required with --ref)",
    )
    parser.add_argument(
        "--command",
        help="Run this one command and exit instead of the prompt",
    )
    args = parser.parse_args()

    if args.artifact and args.ref:
        sys.exit("Use either an artifact id or --ref, not both.")
    if args.artifact:
        snapshot = _snapshot_from_artifact(args.artifact)
    elif args.ref and args.sandbox_id:
        snapshot = SandboxSnapshot(
            sandbox_id=UUID(args.sandbox_id), ref=args.ref
        )
    else:
        sys.exit("Provide an episode artifact id, or --ref + --sandbox-id.")

    sandbox = _load_sandbox(snapshot.sandbox_id)
    print(
        f"Restoring snapshot {snapshot.ref} via sandbox "
        f"'{sandbox.name}' ({sandbox.flavor})..."
    )
    session = sandbox.restore(snapshot)
    print(f"Session {session.id} restored.")

    exit_code = 0
    try:
        if args.command:
            exit_code = _run_command(session, args.command)
        else:
            print("Interactive prompt — 'exit' or Ctrl-D to leave.")
            while True:
                try:
                    command = input("sandbox> ").strip()
                except EOFError:
                    break
                if command in {"exit", "quit"}:
                    break
                if command:
                    _run_command(session, command)
    finally:
        answer: Optional[str] = None
        if not args.command and sys.stdin.isatty():
            answer = input("Destroy restored sandbox? [Y/n] ").strip()
        if answer is None or answer.lower() in {"", "y", "yes"}:
            session.destroy()
            print("Restored sandbox destroyed.")
        else:
            session.close()
            print(
                "Left running — it will live until its TTL expires "
                "or you destroy it on the provider."
            )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
