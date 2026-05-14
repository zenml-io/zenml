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

import zenml.pipelines.pipeline_definition as pipeline_definition_module
from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.config.compiler import Compiler as BaseCompiler
from zenml.config.step_configurations import Step
from zenml.config.step_execution_spec import StepExecutionProtocol
from zenml.zenbabel import build_pipeline_spec, build_steps

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
PORTABLE_STEP_NAME = "score_or_transform"
DEFAULT_THRESHOLD = 0.64


def _typescript_docker_settings() -> DockerSettings:
    """Return the Docker settings for the TypeScript step image."""
    return DockerSettings(
        dockerfile=str(EXAMPLE_DIR / "Dockerfile"),
        build_context_root=str(REPO_ROOT),
        disable_automatic_requirements_detection=True,
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


@step(settings={"docker": _typescript_docker_settings()})
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


@pipeline(enable_cache=False)
def zenbabel_mixed_static() -> None:
    """Python control-plane pipeline with one TypeScript step body."""
    records = load_data()
    scored_bundle = score_or_transform(records, threshold=DEFAULT_THRESHOLD)
    summarize(scored_bundle)


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
        portable_step = self._portable_steps.get(compiled_step.spec.invocation_id)
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


def compile_demo_snapshot() -> None:
    """Compile the demo and print the patched TypeScript step contract."""
    with zenbabel_compiler_bridge():
        zenbabel_mixed_static.prepare()
        snapshot, _, _ = zenbabel_mixed_static._compile()

    portable_step = snapshot.step_configurations[PORTABLE_STEP_NAME]
    execution_spec = portable_step.spec.execution_spec
    assert execution_spec is not None
    assert (
        execution_spec.protocol
        == StepExecutionProtocol.ZENML_PORTABLE_JSON_V1
    )
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
    with zenbabel_compiler_bridge():
        zenbabel_mixed_static()


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
