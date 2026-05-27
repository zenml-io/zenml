#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""ZenML pipeline driving the PydanticAI + Sandbox agent.

Reads the active stack's Sandbox component, lets the PydanticAI agent
loop with a ``run_python`` tool that executes its generated code in the
sandbox, and returns the natural-language answer.
"""

import site
import sys
from pathlib import Path
from typing import Annotated, Any

from agent import run_agent

import zenml
from zenml import pipeline, step
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.sandboxes.base_sandbox import BaseSandboxSettings


def get_docker_settings(
    skip_parent_build: bool = False, **kwargs: Any
) -> DockerSettings:
    """Builds ``DockerSettings`` that work with an editable ZenML install.

    When this example runs against a containerized orchestrator (e.g. the
    Kubernetes stack), the step image needs to include the current ZenML
    source. If ZenML is installed editable from a git checkout (the dev
    workflow), we bake a parent build that copies the editable tree into
    the image. Otherwise we use the published wheel and just install the
    example's requirements on top.

    Harmless when running on the ``default`` orchestrator (which doesn't
    containerize) — the settings are simply ignored.

    Args:
        skip_parent_build: If True, never add the parent build even when
            ZenML appears to be an editable install. Useful when the
            target environment has its own preferred image.
        **kwargs: Extra ``DockerSettings`` fields to merge in.

    Returns:
        A ``DockerSettings`` configured for this example.
    """
    settings_kwargs: dict = {
        "build_config": {
            "build_options": {
                "platform": "linux/amd64",
            }
        },
        "python_package_installer": "uv",
    }

    if not skip_parent_build:
        for path in site.getsitepackages() + [site.getusersitepackages()]:
            if Path(path).resolve() in Path(zenml.__file__).resolve().parents:
                # ZenML is installed from a wheel; nothing to do.
                break
        else:
            # Editable install — add a parent build so the image carries
            # the current ZenML source rather than the published wheel.
            zenml_git_root = Path(zenml.__file__).parents[2]
            settings_kwargs.update(
                {
                    "dockerfile": str(
                        zenml_git_root / "docker" / "zenml-dev.Dockerfile"
                    ),
                    "build_context_root": str(zenml_git_root),
                    "parent_image_build_config": {
                        "build_options": {
                            "platform": "linux/amd64",
                            "buildargs": {
                                "PYTHON_VERSION": (
                                    f"{sys.version_info.major}."
                                    f"{sys.version_info.minor}"
                                )
                            },
                        }
                    },
                    "prevent_build_reuse": True,
                }
            )

    settings_kwargs.update(kwargs)
    settings_kwargs.setdefault("allow_download_from_artifact_store", False)
    settings_kwargs.setdefault("allow_download_from_code_repository", False)

    return DockerSettings(**settings_kwargs)


_AGENT_SANDBOX_SETTINGS = BaseSandboxSettings(
    forward_logs_to_step=True,
    # Agent loops can run >5min on a slow OpenAI day; lift Modal's
    # 5-minute default so a slow tool-use loop doesn't kill the sandbox
    # mid-exec.
    timeout_seconds=900,
)


@step(settings={"sandbox": _AGENT_SANDBOX_SETTINGS})
def agent_step(query: str) -> Annotated[str, "agent_answer"]:
    """Runs the PydanticAI agent against the active stack's Sandbox.

    Args:
        query: The natural-language question.

    Returns:
        The agent's answer.
    """
    return run_agent(query)


@pipeline(
    dynamic=True,
    enable_cache=False,
    settings={
        "docker": get_docker_settings(
            requirements="requirements.txt",
        )
    },
)
def sandbox_pydantic_ai_pipeline(
    query: str = (
        "What's the sum of the first 100 prime numbers? "
        "Write Python to compute it."
    ),
) -> str:
    """Single-step pipeline that drives the PydanticAI agent."""
    return agent_step(query=query)


_PRIMITIVES_SANDBOX_SETTINGS = BaseSandboxSettings(
    forward_logs_to_step=True,
    timeout_seconds=900,
)


@step(settings={"sandbox": _PRIMITIVES_SANDBOX_SETTINGS})
def upload_exec_download_step() -> Annotated[str, "round_trip_payload"]:
    """Exercises upload_file -> exec -> download_file.

    Writes a local file into the sandbox, runs a Python command that reads
    the file and writes a result, then downloads the result back. Confirms
    the basic IO surface works on the active sandbox flavor.

    Returns:
        The string the sandbox wrote back, after a local round trip.
    """
    import tempfile
    from pathlib import Path

    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")

    with tempfile.TemporaryDirectory() as tmp:
        local_in = Path(tmp) / "input.txt"
        local_in.write_text("hello from zenml\n")
        local_out = Path(tmp) / "output.txt"

        with sandbox.create_session() as session:
            session.upload_file(str(local_in), "/tmp/input.txt")
            process = session.exec(
                [
                    "python",
                    "-u",
                    "-c",
                    (
                        "import pathlib; "
                        "src = pathlib.Path('/tmp/input.txt').read_text(); "
                        "pathlib.Path('/tmp/output.txt').write_text("
                        "src.upper())"
                    ),
                ]
            )
            result = process.collect()
            if result.exit_code != 0:
                raise RuntimeError(
                    f"Sandbox exec failed (code={result.exit_code}): "
                    f"{result.stderr}"
                )
            session.download_file("/tmp/output.txt", str(local_out))

        return local_out.read_text()


@step(settings={"sandbox": _PRIMITIVES_SANDBOX_SETTINGS})
def snapshot_step() -> Annotated[Any, "session_snapshot"]:
    """Snapshots a sandbox session after seeding state.

    Boots a session, writes a marker file, snapshots, then returns the
    snapshot for a downstream step to restore. Requires a flavor that
    implements ``snapshot`` (e.g. Modal).

    Returns:
        The opaque snapshot handle.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")

    with sandbox.create_session() as session:
        process = session.exec(
            [
                "python",
                "-u",
                "-c",
                (
                    "import pathlib; "
                    "pathlib.Path('/tmp/marker.txt').write_text("
                    "'pre-snapshot state')"
                ),
            ]
        )
        result = process.collect()
        if result.exit_code != 0:
            raise RuntimeError(
                f"Seeding snapshot state failed: {result.stderr}"
            )
        return session.snapshot()


@step(settings={"sandbox": _PRIMITIVES_SANDBOX_SETTINGS})
def restore_step(snapshot: Any) -> Annotated[str, "restored_marker"]:
    """Restores from a snapshot and reads the marker file back.

    Args:
        snapshot: Snapshot handle produced by ``snapshot_step``.

    Returns:
        The marker text observed after restore. Confirms state survived
        the snapshot/restore round trip.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")

    with sandbox.restore(snapshot) as session:
        process = session.exec(
            [
                "python",
                "-u",
                "-c",
                (
                    "import pathlib; "
                    "print(pathlib.Path('/tmp/marker.txt').read_text())"
                ),
            ]
        )
        result = process.collect()
        if result.exit_code != 0:
            raise RuntimeError(
                f"Restore-read failed (code={result.exit_code}): "
                f"{result.stderr}"
            )
        return result.stdout.strip()


@pipeline(
    dynamic=True,
    enable_cache=False,
    settings={
        "docker": get_docker_settings(requirements="requirements.txt"),
    },
)
def sandbox_primitives_pipeline() -> None:
    """Exercises upload/exec/download then snapshot/restore.

    Snapshot/restore is Modal-only at the moment; on flavors that don't
    implement it the snapshot_step will raise NotImplementedError. Run
    on the modal stack to see the full chain.
    """
    upload_exec_download_step()
    snapshot = snapshot_step()
    restore_step(snapshot=snapshot)


if __name__ == "__main__":
    import sys

    pipeline_name = sys.argv[1] if len(sys.argv) > 1 else "agent"
    if pipeline_name == "primitives":
        print("Running sandbox primitives pipeline...")
        sandbox_primitives_pipeline()
    else:
        print("Running PydanticAI + Sandbox pipeline...")
        sandbox_pydantic_ai_pipeline()
    print("Done. Check the ZenML dashboard for the run + log stream.")
