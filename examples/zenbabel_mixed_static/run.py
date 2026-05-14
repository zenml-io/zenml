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
"""Mixed Python + TypeScript ZenBabel static pipeline example.

This file intentionally keeps the bridge small and local to the example. ZenML
can already execute portable JSON steps once a compiled step contains a
``StepExecutionSpec``. What ZenML does not have yet is a public TypeScript step
SDK that lets users call a TypeScript step directly from a Python ``@pipeline``.

The example therefore uses a normal Python placeholder step for graph building,
then swaps only that placeholder's compiled source/execution metadata for the
portable metadata produced by ``zenml.zenbabel.build_steps``.
"""

import argparse
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import urlparse, urlunparse

import zenml.pipelines.pipeline_definition as pipeline_definition_module
from zenml import pipeline, step
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.config.compiler import Compiler as BaseCompiler
from zenml.config.docker_settings import DockerBuildConfig
from zenml.config.global_config import GlobalConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_execution_spec import StepExecutionProtocol
from zenml.enums import StoreType
from zenml.execution.pipeline.utils import submit_pipeline
from zenml.models import PipelineSnapshotResponse
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.zenbabel import build_pipeline_spec, build_steps

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
PORTABLE_STEP_NAME = "score_or_transform"
DEFAULT_THRESHOLD = 0.64
LOCAL_DOCKER_HOSTNAME = "host.docker.internal"
LOCAL_DOCKER_LOOPBACK_HOSTS = {"127.0.0.1", "localhost"}


def _zenbabel_docker_settings() -> DockerSettings:
    """Return the Docker settings for the mixed-language demo image."""
    return DockerSettings(
        dockerfile=str(EXAMPLE_DIR / "Dockerfile"),
        build_context_root=str(REPO_ROOT),
        parent_image_build_config=DockerBuildConfig(
            dockerignore=str(EXAMPLE_DIR / "Dockerfile.dockerignore"),
        ),
        disable_automatic_requirements_detection=True,
        install_stack_requirements=False,
        prevent_build_reuse=True,
    )


@step
def load_data() -> list[dict[str, Any]]:
    """Load a tiny JSON-shaped dataset in Python."""
    return [
        {"id": "order-001", "feature": 0.12, "segment": "small"},
        {"id": "order-002", "feature": 0.71, "segment": "enterprise"},
        {"id": "order-003", "feature": 0.49, "segment": "small"},
    ]


@step
def score_or_transform(
    records: list[dict[str, Any]], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, Any]:
    """Placeholder compiled as a normal step, then routed to TypeScript."""
    raise RuntimeError(
        "The Python placeholder step `score_or_transform` should have been "
        "replaced by the ZenBabel demo compiler bridge. If you see this, run "
        "the pipeline through `zenbabel_compiler_bridge()`."
    )


@step
def summarize(scored_bundle: dict[str, Any]) -> dict[str, Any]:
    """Summarize the TypeScript step output back in Python."""
    records = scored_bundle["records"]
    accepted = [record for record in records if record["label"] == "accept"]
    summary = {
        "total_records": len(records),
        "accepted_records": len(accepted),
        "threshold": scored_bundle["metadata"]["threshold"],
        "accepted_ids": [record["id"] for record in accepted],
    }
    print(f"Python summary received TypeScript output: {summary}")
    return summary


@pipeline(
    enable_cache=False,
    enable_heartbeat=False,
    settings={"docker": _zenbabel_docker_settings()},
)
def zenbabel_mixed_static() -> None:
    """Python control-plane pipeline with one TypeScript step body."""
    records = load_data()
    scored_bundle = score_or_transform(records, threshold=DEFAULT_THRESHOLD)
    summarize(scored_bundle)


def _container_store_environment() -> dict[str, str]:
    """Return store env vars that work from inside Local Docker steps."""
    store_config = GlobalConfiguration().store_configuration
    if store_config.type != StoreType.REST:
        raise RuntimeError(
            "The ZenBabel mixed static demo needs a REST ZenML store when "
            "running with Local Docker. Start a local ZenML server from this "
            "worktree with `uv run zenml login --local --restart`, then run "
            "the demo again."
        )

    store_url = store_config.url
    parsed_url = urlparse(store_url)
    if parsed_url.hostname in LOCAL_DOCKER_LOOPBACK_HOSTS:
        if parsed_url.port is None:
            netloc = LOCAL_DOCKER_HOSTNAME
        else:
            netloc = f"{LOCAL_DOCKER_HOSTNAME}:{parsed_url.port}"
        store_url = urlunparse(parsed_url._replace(netloc=netloc))

    return {
        "ZENML_STORE_TYPE": StoreType.REST.value,
        "ZENML_STORE_URL": store_url,
    }


def _zenbabel_external_spec() -> dict[str, Any]:
    """Return the external TypeScript step spec used by the demo bridge."""
    return {
        "name": "zenbabel_mixed_static",
        "steps": [
            {
                "name": PORTABLE_STEP_NAME,
                "command": [
                    "node",
                    "/app/dist/steps/score_or_transform.js",
                ],
                "source_identity": (
                    "examples/zenbabel_mixed_static/ts/src/steps/"
                    "score_or_transform.ts#scoreOrTransform"
                ),
                "parameters": {"threshold": DEFAULT_THRESHOLD},
                "outputs": ["output"],
            }
        ],
        "outputs": [{"step": PORTABLE_STEP_NAME, "output": "output"}],
    }


class ZenBabelDemoCompiler(BaseCompiler):
    """Example-local compiler that donates portable metadata to one step."""

    def __init__(self, portable_steps: Mapping[str, Step]) -> None:
        """Initialize the compiler bridge.

        Args:
            portable_steps: Portable metadata donor steps keyed by invocation id.
        """
        super().__init__()
        self._portable_steps = portable_steps

    def _compile_step_invocation(self, *args: Any, **kwargs: Any) -> Step:
        """Compile normally, then route selected invocations to ZenBabel."""
        compiled_step = super()._compile_step_invocation(*args, **kwargs)
        portable_step = self._portable_steps.get(
            compiled_step.spec.invocation_id
        )
        if portable_step is None:
            return compiled_step

        patched_spec = compiled_step.spec.model_copy(
            update={
                "source": portable_step.spec.source,
                "execution_spec": portable_step.spec.execution_spec,
            }
        )
        return compiled_step.model_copy(update={"spec": patched_spec})


@contextmanager
def zenbabel_compiler_bridge() -> Iterator[None]:
    """Temporarily route the demo placeholder step through ZenBabel.

    This is not a product API. It is deliberately scoped to this example so the
    already implemented portable runner can be exercised without broadening the
    public SDK surface.
    """
    original_compiler = pipeline_definition_module.Compiler
    portable_steps = build_steps(_zenbabel_external_spec())

    def compiler_factory() -> ZenBabelDemoCompiler:
        return ZenBabelDemoCompiler(portable_steps=portable_steps)

    pipeline_definition_module.Compiler = compiler_factory  # type: ignore[assignment]
    try:
        yield
    finally:
        pipeline_definition_module.Compiler = original_compiler


def _validate_portable_execution_spec(
    snapshot: PipelineSnapshotResponse,
) -> None:
    """Check that the portable step survived snapshot persistence."""
    portable_step = snapshot.step_configurations[PORTABLE_STEP_NAME]
    execution_spec = portable_step.spec.execution_spec
    if (
        execution_spec is None
        or execution_spec.protocol
        != StepExecutionProtocol.ZENML_PORTABLE_JSON_V1
    ):
        raise RuntimeError(
            "The ZenBabel demo compiled `score_or_transform` as a portable "
            "TypeScript step, but the created snapshot returned by the "
            "active ZenML server/store no longer contains "
            "`spec.execution_spec = zenml-portable-json-v1`. This usually "
            "means the active ZenML server/store does not include this "
            "experimental branch schema and stripped the field during the "
            "server/store round trip. If you are connected to a local daemon, "
            "make sure that daemon was started from this worktree's virtual "
            "environment, for example with `uv run zenml login --local "
            "--restart`. If you are connected to Cloud/staging, deploy a "
            "backend from this branch before running the full demo."
        )


def _validate_local_docker_stack() -> None:
    """Check that the active stack can run the TypeScript Docker step."""
    stack = Client().active_stack
    orchestrator = stack.orchestrator
    if orchestrator.flavor != "local_docker":
        raise RuntimeError(
            "The ZenBabel mixed static demo needs the Local Docker "
            "orchestrator because the pipeline uses Docker settings to "
            "build and run a Node-enabled image containing this branch's "
            "ZenML code. The "
            f"active stack `{stack.name}` uses orchestrator "
            f"`{orchestrator.name}` with flavor `{orchestrator.flavor}`. "
            "Set a stack with a `local_docker` orchestrator and a local image "
            "builder, or run `uv run python "
            "examples/zenbabel_mixed_static/run.py --compile-only` instead."
        )
    if stack.image_builder is None:
        raise RuntimeError(
            "The ZenBabel mixed static demo needs an image builder on the "
            "active stack. The pipeline has Docker settings pointing at "
            "`examples/zenbabel_mixed_static/Dockerfile`, so ZenML must "
            "build the demo image before Local Docker can run it. Register "
            "and set a stack with a local image builder, or run "
            "`uv run python examples/zenbabel_mixed_static/run.py "
            "--compile-only` instead."
        )


def compile_demo_snapshot() -> None:
    """Compile the demo and print the patched TypeScript step contract."""
    with zenbabel_compiler_bridge():
        zenbabel_mixed_static.prepare()
        snapshot, _, _ = zenbabel_mixed_static._compile()

    _validate_portable_execution_spec(snapshot)
    portable_step = snapshot.step_configurations[PORTABLE_STEP_NAME]
    execution_spec = portable_step.spec.execution_spec
    assert execution_spec is not None
    assert portable_step.spec.inputs["records"].step_name == "load_data"
    assert portable_step.spec.upstream_steps == ["load_data"]
    assert "docker" in portable_step.config.settings

    importer_spec = build_pipeline_spec(_zenbabel_external_spec())
    print("Compiled ZenBabel demo snapshot successfully.")
    print(f"Pipeline spec version: {snapshot.pipeline_spec.version}")
    print(f"Importer-only portable spec version: {importer_spec.version}")
    print(f"Portable command: {execution_spec.command}")
    print(f"Portable source: {execution_spec.source_identity}")


def run_pipeline() -> None:
    """Run the mixed-language pipeline on the active ZenML stack."""
    _validate_local_docker_stack()
    runtime_pipeline = zenbabel_mixed_static.with_options(
        environment=_container_store_environment()
    )
    with zenbabel_compiler_bridge():
        runtime_pipeline.prepare()
        snapshot = runtime_pipeline._create_snapshot()

    _validate_portable_execution_spec(snapshot)
    run = create_placeholder_run(snapshot=snapshot)
    submit_pipeline(
        snapshot=snapshot, stack=Client().active_stack, placeholder_run=run
    )


def main() -> None:
    """CLI entrypoint for the example."""
    parser = argparse.ArgumentParser(
        description="Run or compile the ZenBabel mixed static example."
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile the patched snapshot without submitting a pipeline run.",
    )
    args = parser.parse_args()

    if args.compile_only:
        compile_demo_snapshot()
    else:
        run_pipeline()


if __name__ == "__main__":
    main()
