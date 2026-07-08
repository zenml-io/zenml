"""On-disk coordination between the trainer and rollout pipelines.

All shared state (weights, queue, markers) lives under one sub-directory of
the active stack's artifact store, and every read and write goes through
ZenML's `fileio`. On a local artifact store that is the local filesystem.
Point the stack at S3 or GCS and the same code coordinates over object
storage with no changes.

    <artifact_store>/<run_name>/
      versions/v{n}/adapter/   + v{n}/LIVE (servable) | v{n}/RETIRED (shutting down)
      current                  atomic pointer: newest live version
      rollouts/pending/        generators drop complete groups here
      rollouts/claimed/        trainer moves a group here while consuming it
      STOP                     presence = drain and exit

A "version" stands in for a deployed vLLM instance. Here it is a LoRA
adapter directory plus a liveness marker. `max_versions` is the staleness
window: rollouts generated against a version older than the window are
dropped, and a version that ages out is retired, which makes any generation
still running against it fail gracefully.

Weights are staged local<->store because torch reads and writes local
paths. Coordination files are read and written in place via `fileio`.
"""

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from zenml.client import Client
from zenml.io import fileio
from zenml.utils import io_utils

LIVE_MARKER = "LIVE"
RETIRED_MARKER = "RETIRED"


def resolve_run_root(run_name: str) -> str:
    """Resolve a run name to a sub-directory of the active artifact store.

    Args:
        run_name: Name of the run's shared sub-directory.

    Returns:
        The full artifact-store path shared by both pipelines.
    """
    return os.path.join(Client().active_stack.artifact_store.path, run_name)


def init_run_dir(root: str) -> None:
    """Create the shared directory layout if it does not exist yet.

    Args:
        root: The run directory shared by both pipelines.
    """
    fileio.makedirs(os.path.join(root, "versions"))
    fileio.makedirs(os.path.join(root, "rollouts", "pending"))
    fileio.makedirs(os.path.join(root, "rollouts", "claimed"))


def version_root(root: str, version: int) -> str:
    """Return the directory holding one version's adapter and markers.

    Args:
        root: The run directory.
        version: Version number.

    Returns:
        Path to versions/v{version}.
    """
    return os.path.join(root, "versions", f"v{version}")


def adapter_dir(root: str, version: int) -> str:
    """Return the store path of a version's adapter directory.

    Args:
        root: The run directory.
        version: Version number.

    Returns:
        Path to the version's adapter directory in the artifact store.
    """
    return os.path.join(version_root(root, version), "adapter")


def mark_live(root: str, version: int) -> None:
    """Mark a version as servable.

    Args:
        root: The run directory.
        version: Version number.
    """
    io_utils.write_file_contents_as_string(
        os.path.join(version_root(root, version), LIVE_MARKER), ""
    )


def is_live(root: str, version: int) -> bool:
    """Return whether a version is still servable.

    Args:
        root: The run directory.
        version: Version number.

    Returns:
        True if the LIVE marker is present.
    """
    return fileio.exists(
        os.path.join(version_root(root, version), LIVE_MARKER)
    )


def set_current(root: str, version: int) -> None:
    """Atomically point `current` at a version.

    Args:
        root: The run directory.
        version: Version number.
    """
    dst = os.path.join(root, "current")
    tmp = os.path.join(root, f".current.{uuid.uuid4().hex}")
    io_utils.write_file_contents_as_string(tmp, str(version))
    fileio.rename(tmp, dst, overwrite=True)


def get_current(root: str) -> Optional[int]:
    """Read the current version pointer.

    Args:
        root: The run directory.

    Returns:
        The current version, or None if the trainer has not published one.
    """
    path = os.path.join(root, "current")
    if not fileio.exists(path):
        return None
    try:
        return int(io_utils.read_file_contents_as_string(path).strip())
    except ValueError:
        return None


def publish_version(root: str, version: int) -> None:
    """Make a version live and current.

    Marks LIVE before flipping `current` so a generator that sees the new
    pointer always finds the version live.

    Args:
        root: The run directory.
        version: Version number whose adapter is already staged.
    """
    mark_live(root, version)
    set_current(root, version)


def live_versions(root: str) -> List[int]:
    """List live versions, oldest first.

    Args:
        root: The run directory.

    Returns:
        Sorted version numbers that still carry a LIVE marker.
    """
    versions = []
    versions_root = os.path.join(root, "versions")
    for name in fileio.listdir(versions_root):
        if name.startswith("v") and fileio.exists(
            os.path.join(versions_root, name, LIVE_MARKER)
        ):
            try:
                versions.append(int(name[1:]))
            except ValueError:
                continue
    return sorted(versions)


def mark_retired(root: str, version: int) -> None:
    """Signal a version's shutdown by retiring its liveness marker.

    Any generation still running against it will see the missing LIVE
    marker and abort gracefully. The retirement time is stored in the
    marker so gc can honor a grace period on any filesystem.

    Args:
        root: The run directory.
        version: Version number.
    """
    io_utils.write_file_contents_as_string(
        os.path.join(version_root(root, version), RETIRED_MARKER),
        str(time.time()),
    )
    live = os.path.join(version_root(root, version), LIVE_MARKER)
    if fileio.exists(live):
        fileio.remove(live)


def gc_retired(root: str, grace_seconds: float) -> None:
    """Delete adapter directories retired longer than the grace period.

    The grace period keeps a just-retired adapter available long enough
    for an in-flight generator that already started staging it to finish.

    Args:
        root: The run directory.
        grace_seconds: Seconds a version must stay retired before deletion.
    """
    now = time.time()
    versions_root = os.path.join(root, "versions")
    for name in fileio.listdir(versions_root):
        if not name.startswith("v"):
            continue
        retired = os.path.join(versions_root, name, RETIRED_MARKER)
        if not fileio.exists(retired):
            continue
        try:
            retired_at = float(io_utils.read_file_contents_as_string(retired))
        except ValueError:
            retired_at = 0.0
        if now - retired_at > grace_seconds:
            fileio.rmtree(os.path.join(versions_root, name))


def stage_adapter_in(local_dir: str, root: str, version: int) -> None:
    """Upload a local adapter directory into a version's store location.

    Args:
        local_dir: Local adapter directory to upload.
        root: The run directory.
        version: Version number to publish the adapter as.
    """
    io_utils.copy_dir(str(local_dir), adapter_dir(root, version), overwrite=True)


def stage_adapter_out(root: str, version: int) -> str:
    """Download a version's adapter from the store to a local directory.

    Args:
        root: The run directory.
        version: Version number.

    Returns:
        Path to a fresh local directory holding the adapter.
    """
    local_dir = tempfile.mkdtemp(prefix=f"async-rl-adapter-v{version}-")
    io_utils.copy_dir(adapter_dir(root, version), local_dir, overwrite=True)
    return local_dir


def enqueue_group(
    root: str, version: int, episodes: List[Dict[str, Any]]
) -> None:
    """Atomically add one complete, scored group to the rollout queue.

    The unit is a full GRPO group (group_size completions of one task at
    one version), because the trainer cannot form a GRPO batch from
    partial groups.

    Args:
        root: The run directory.
        version: Version the group was generated against.
        episodes: The group's scored episode records.
    """
    pending = os.path.join(root, "rollouts", "pending")
    name = f"v{version:08d}_{time.time_ns()}_{uuid.uuid4().hex}.json"
    tmp = os.path.join(pending, f".tmp.{uuid.uuid4().hex}")
    io_utils.write_file_contents_as_string(
        tmp, json.dumps({"version": version, "episodes": episodes})
    )
    fileio.rename(tmp, os.path.join(pending, name), overwrite=True)


@dataclass
class ClaimedGroup:
    """A rollout group the trainer has taken off the queue."""

    version: int
    episodes: List[Dict[str, Any]]
    path: str


@dataclass
class ClaimResult:
    """Result of one queue claim."""

    groups: List[ClaimedGroup]
    dropped_stale: int


def _pending_group_names(pending: str) -> List[str]:
    return [
        name
        for name in fileio.listdir(pending)
        if name.startswith("v") and name.endswith(".json")
    ]


def claim_groups(root: str, max_groups: int, min_version: int) -> ClaimResult:
    """Take up to max_groups fresh groups, dropping any below the window.

    Groups older than min_version are deleted rather than trained on.
    Remaining groups are returned freshest first.

    Args:
        root: The run directory.
        max_groups: Maximum groups to claim this step.
        min_version: Oldest version still inside the staleness window.

    Returns:
        The claimed groups and a count of stale groups dropped.
    """
    pending = os.path.join(root, "rollouts", "pending")
    claimed = os.path.join(root, "rollouts", "claimed")

    dropped = 0
    fresh = []
    for name in _pending_group_names(pending):
        try:
            version = int(name[1:9])
        except ValueError:
            continue
        if version < min_version:
            fileio.remove(os.path.join(pending, name))
            dropped += 1
        else:
            fresh.append((version, name))

    fresh.sort(key=lambda item: item[0], reverse=True)

    groups = []
    for version, name in fresh[:max_groups]:
        dst = os.path.join(claimed, name)
        try:
            fileio.rename(os.path.join(pending, name), dst, overwrite=True)
        except Exception:
            continue
        payload = json.loads(io_utils.read_file_contents_as_string(dst))
        groups.append(
            ClaimedGroup(
                version=version, episodes=payload["episodes"], path=dst
            )
        )
    return ClaimResult(groups=groups, dropped_stale=dropped)


def discard_group(path: str) -> None:
    """Delete a claimed group file after it has been consumed.

    Args:
        path: Store path of the claimed group.
    """
    if fileio.exists(path):
        fileio.remove(path)


def queue_depth(root: str) -> int:
    """Return the number of groups waiting in the queue.

    Args:
        root: The run directory.

    Returns:
        Count of pending group files.
    """
    return len(_pending_group_names(os.path.join(root, "rollouts", "pending")))


def signal_stop(root: str) -> None:
    """Ask both pipelines to drain and exit.

    Args:
        root: The run directory.
    """
    io_utils.write_file_contents_as_string(os.path.join(root, "STOP"), "")


def stop_requested(root: str) -> bool:
    """Return whether a stop has been signalled.

    Args:
        root: The run directory.

    Returns:
        True if the STOP marker is present.
    """
    return fileio.exists(os.path.join(root, "STOP"))
