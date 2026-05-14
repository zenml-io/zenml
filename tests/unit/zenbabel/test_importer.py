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
"""Tests for the experimental ZenBabel external spec importer."""

from typing import Any, Dict

import pytest

from zenml.config.step_configurations import InputSpec, Step
from zenml.config.step_execution_spec import (
    StepExecutionLanguage,
    StepExecutionProtocol,
)
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE
from zenml.zenbabel.external_spec import ExternalPipelineSpec
from zenml.zenbabel.importer import (
    build_pipeline_snapshot,
    build_pipeline_spec,
    build_steps,
)


def _external_spec() -> Dict[str, Any]:
    """Return a small static external pipeline spec."""
    return {
        "name": "zenbabel_demo",
        "steps": [
            {
                "name": "load_data",
                "command": ["node", "/app/dist/steps/load_data.js"],
                "source_identity": "ts/src/steps/load_data.ts#loadData",
                "outputs": ["records"],
                "parameters": {"limit": 3},
            },
            {
                "name": "score",
                "command": ["node", "/app/dist/steps/score.js"],
                "source_identity": "ts/src/steps/score.ts#score",
                "inputs": {
                    "records": {"step": "load_data", "output": "records"}
                },
                "outputs": ["scores"],
            },
        ],
        "outputs": [{"step": "score", "output": "scores"}],
    }


def test_external_spec_builds_normal_zenml_steps() -> None:
    """External TypeScript steps become normal ZenML step objects."""
    steps = build_steps(_external_spec())

    assert list(steps) == ["load_data", "score"]
    assert all(isinstance(step, Step) for step in steps.values())

    load_data = steps["load_data"]
    assert load_data.spec.source.import_path == PORTABLE_STEP_ADAPTER_SOURCE
    assert load_data.spec.invocation_id == "load_data"
    assert load_data.spec.upstream_steps == []
    assert load_data.config.name == "load_data"
    assert load_data.config.parameters == {"limit": 3}
    assert set(load_data.config.outputs) == {"records"}

    execution_spec = load_data.spec.execution_spec
    assert execution_spec is not None
    assert execution_spec.language == StepExecutionLanguage.TYPESCRIPT
    assert (
        execution_spec.protocol == StepExecutionProtocol.ZENML_PORTABLE_JSON_V1
    )
    assert execution_spec.command == ["node", "/app/dist/steps/load_data.js"]
    assert (
        execution_spec.source_identity == "ts/src/steps/load_data.ts#loadData"
    )


def test_external_spec_maps_inputs_and_upstream_dependencies() -> None:
    """Data inputs become InputSpec objects and upstream step dependencies."""
    steps = build_steps(
        {
            "name": "fan_in_demo",
            "steps": [
                {
                    "name": "first",
                    "command": ["node", "first.js"],
                    "source_identity": "ts/first.ts#first",
                    "outputs": ["value"],
                },
                {
                    "name": "second",
                    "command": ["node", "second.js"],
                    "source_identity": "ts/second.ts#second",
                    "outputs": ["value"],
                },
                {
                    "name": "combine",
                    "command": ["node", "combine.js"],
                    "source_identity": "ts/combine.ts#combine",
                    "inputs": {
                        "primary": {"step": "first", "output": "value"},
                        "others": [
                            {"step": "first", "output": "value"},
                            {"step": "second", "output": "value"},
                        ],
                    },
                    "depends_on": ["second"],
                    "outputs": ["combined"],
                },
            ],
        }
    )

    combine = steps["combine"]
    assert combine.spec.upstream_steps == ["first", "second"]
    assert combine.spec.inputs["primary"] == InputSpec(
        step_name="first", output_name="value"
    )
    assert combine.spec.inputs["others"] == [
        InputSpec(step_name="first", output_name="value"),
        InputSpec(step_name="second", output_name="value"),
    ]


def test_external_spec_builds_portable_pipeline_spec_serialization() -> None:
    """Generated pipeline specs use the conditional portable serialization."""
    pipeline_spec = build_pipeline_spec(_external_spec())

    assert pipeline_spec.version == "0.6"
    assert [step.invocation_id for step in pipeline_spec.steps] == [
        "load_data",
        "score",
    ]
    assert pipeline_spec.outputs[0].step_name == "score"
    assert pipeline_spec.outputs[0].output_name == "scores"

    dumped = pipeline_spec.model_dump(mode="json")
    score_spec = dumped["steps"][1]
    assert score_spec["source"]["module"] == "zenml.zenbabel.adapters"
    assert score_spec["source"]["attribute"] == "PortableStepAdapter"
    assert score_spec["execution_spec"] == {
        "language": "typescript",
        "protocol": "zenml-portable-json-v1",
        "command": ["node", "/app/dist/steps/score.js"],
        "source_identity": "ts/src/steps/score.ts#score",
    }

    serialized = pipeline_spec.json_with_string_sources
    assert '"version": "0.6"' in serialized
    assert PORTABLE_STEP_ADAPTER_SOURCE in serialized
    assert "ts/src/steps/score.ts#score" in serialized


def test_external_spec_builds_minimal_static_snapshot() -> None:
    """The importer can produce a minimal static PipelineSnapshotBase."""
    snapshot = build_pipeline_snapshot(
        _external_spec(),
        run_name_template="portable-run-{date}",
        client_environment={"runtime": "test"},
        client_version="0.0.test",
        server_version="0.0.test",
    )

    assert snapshot.run_name_template == "portable-run-{date}"
    assert snapshot.pipeline_configuration.name == "zenbabel_demo"
    assert snapshot.is_dynamic is False
    assert snapshot.client_environment == {"runtime": "test"}
    assert snapshot.client_version == "0.0.test"
    assert snapshot.server_version == "0.0.test"
    assert snapshot.pipeline_version_hash
    assert list(snapshot.step_configurations) == ["load_data", "score"]
    assert snapshot.pipeline_spec is not None
    assert snapshot.pipeline_spec.version == "0.6"


def test_external_spec_rejects_dynamic_graphs() -> None:
    """Dynamic pipeline declarations fail before ZenML object creation."""
    spec = _external_spec()
    spec["graph"] = "dynamic"

    with pytest.raises(ValueError, match="only support static pipelines"):
        ExternalPipelineSpec.model_validate(spec)


def test_external_spec_rejects_unsupported_step_protocol() -> None:
    """Non-portable protocols fail clearly."""
    spec = _external_spec()
    spec["steps"][0]["protocol"] = "zenml-python-step-v1"

    with pytest.raises(ValueError, match="zenml-portable-json-v1"):
        ExternalPipelineSpec.model_validate(spec)


def test_external_spec_rejects_unknown_or_cyclic_graph_shapes() -> None:
    """Unsupported static graph references fail with clear messages."""
    unknown = _external_spec()
    unknown["steps"][1]["inputs"] = {
        "records": {"step": "missing", "output": "records"}
    }

    with pytest.raises(ValueError, match="unknown upstream step `missing`"):
        ExternalPipelineSpec.model_validate(unknown)

    cyclic = {
        "name": "cycle_demo",
        "steps": [
            {
                "name": "first",
                "command": ["node", "first.js"],
                "source_identity": "ts/first.ts#first",
                "depends_on": ["second"],
            },
            {
                "name": "second",
                "command": ["node", "second.js"],
                "source_identity": "ts/second.ts#second",
                "depends_on": ["first"],
            },
        ],
    }

    with pytest.raises(ValueError, match="acyclic static pipelines"):
        ExternalPipelineSpec.model_validate(cyclic)
