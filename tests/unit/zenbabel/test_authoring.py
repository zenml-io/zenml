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
"""Tests for the experimental ZenBabel authoring helpers."""

import zenml.pipelines.pipeline_definition as pipeline_definition_module
from zenml.config.step_configurations import InputSpec
from zenml.utils import source_utils
from zenml.zenbabel.authoring import (
    ExperimentalPortableStepCompiler,
    _replace_with_portable_execution,
    experimental_portable_json_compiler_bridge,
    experimental_portable_json_pipeline_spec,
    experimental_portable_json_step,
)
from zenml.zenbabel.importer import build_steps


def _placeholder_step() -> None:
    """Placeholder source used for authoring helper tests."""


def _portable_spec() -> object:
    """Return a tiny portable authoring spec."""
    return experimental_portable_json_pipeline_spec(
        name="authoring_demo",
        steps=[
            experimental_portable_json_step(
                name="score",
                command=["node", "/app/dist/score.js"],
                source_identity="ts/src/score.ts#score",
                parameters={"threshold": 0.5},
            )
        ],
        outputs=[("score", "output")],
    )


def test_authoring_bridge_patches_and_restores_pipeline_compiler() -> None:
    """The compiler bridge is scoped to its context manager."""
    original_compiler = pipeline_definition_module.Compiler

    with experimental_portable_json_compiler_bridge(_portable_spec()):
        compiler = pipeline_definition_module.Compiler()
        assert isinstance(compiler, ExperimentalPortableStepCompiler)

    assert pipeline_definition_module.Compiler is original_compiler


def test_authoring_bridge_copies_only_portable_routing_metadata() -> None:
    """Placeholder graph wiring survives the portable metadata swap."""
    portable_step = build_steps(_portable_spec())["score"]
    compiled_spec = portable_step.spec.model_copy(
        update={
            "source": source_utils.resolve(_placeholder_step),
            "execution_spec": None,
            "inputs": {
                "records": InputSpec(
                    step_name="load_data", output_name="output"
                )
            },
            "upstream_steps": ["load_data"],
        }
    )
    compiled_step = portable_step.model_copy(update={"spec": compiled_spec})

    patched_step = _replace_with_portable_execution(
        compiled_step=compiled_step,
        portable_step=portable_step,
    )

    assert patched_step.spec.source == portable_step.spec.source
    assert (
        patched_step.spec.execution_spec == portable_step.spec.execution_spec
    )
    assert patched_step.spec.inputs == compiled_step.spec.inputs
    assert patched_step.spec.upstream_steps == ["load_data"]
    assert patched_step.config == compiled_step.config
