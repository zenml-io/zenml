"""Unit tests for ZenBabel portable JSON step execution."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.materializers.built_in_materializer import (
    BuiltInContainerMaterializer,
    BuiltInMaterializer,
)
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.orchestrators.portable_step_runner import (
    PortableJSONValueError,
    PortableStepRunner,
    validate_portable_json_value,
)
from zenml.orchestrators.step_runner import StepRunner
from zenml.stack import Stack
from zenml.utils import source_utils
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE


def _portable_step(
    command: list[str],
    parameters: Dict[str, Any] | None = None,
    enable_heartbeat: bool = False,
    output_materializer_source: tuple[Any, ...] = (),
) -> Step:
    return Step.model_validate(
        {
            "spec": {
                "source": PORTABLE_STEP_ADAPTER_SOURCE,
                "upstream_steps": [],
                "invocation_id": "portable_step",
                "enable_heartbeat": enable_heartbeat,
                "execution_spec": {
                    "language": "typescript",
                    "protocol": "zenml-portable-json-v1",
                    "command": command,
                    "source_identity": "tests/portable_step.ts#portable_step",
                },
            },
            "config": {
                "name": "portable_step",
                "parameters": parameters or {},
                "outputs": {
                    "output": {
                        "materializer_source": output_materializer_source
                    }
                },
            },
        }
    )


def _step_run_info(
    step: Step,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> StepRunInfo:
    return StepRunInfo(
        step_run_id=uuid4(),
        run_id=uuid4(),
        run_name="run_name",
        pipeline_step_name="portable_step",
        config=step.config,
        spec=step.spec,
        pipeline=PipelineConfiguration(name="pipeline_name"),
        snapshot=sample_snapshot_response_model,
        force_write_logs=lambda: None,
        step_run=sample_step_run,
    )


def _patch_runner_side_effects(
    mocker: Any, stored_outputs: Dict[str, Any] | None = None
) -> None:
    mocker.patch.object(Stack, "prepare_step_run")
    mocker.patch.object(Stack, "cleanup_step_run")
    mocker.patch(
        "zenml.orchestrators.portable_step_runner.publish_step_run_metadata"
    )
    mocker.patch(
        "zenml.orchestrators.portable_step_runner.publish_successful_step_run"
    )
    mocker.patch(
        "zenml.orchestrators.portable_step_runner.publish_failed_step_run",
        return_value=MagicMock(is_retriable=False),
    )
    mocker.patch(
        "zenml.orchestrators.portable_step_runner.setup_logging_context",
        return_value=mocker.MagicMock(
            __enter__=lambda s: None, __exit__=lambda s, *a: None
        ),
    )

    def _store_output_artifacts(
        self: StepRunner, output_data: Dict[str, Any], **_: Any
    ) -> Dict[str, Any]:
        if stored_outputs is not None:
            stored_outputs.update(output_data)
        return {name: MagicMock(id=uuid4()) for name in output_data}

    mocker.patch.object(
        StepRunner,
        "_store_output_artifacts",
        _store_output_artifacts,
    )


def test_portable_json_validation_rejects_non_json_shapes() -> None:
    """Strict portable JSON rejects values that Python JSON might coerce."""
    invalid_values = [
        ("tuple", (1, 2)),
        ("set", {1, 2}),
        ("non_string_key", {1: "one"}),
        ("nan", float("nan")),
        ("unsafe_integer", 2**53),
        ("object", object()),
    ]

    for label, value in invalid_values:
        with pytest.raises(PortableJSONValueError, match="Portable JSON"):
            validate_portable_json_value(value, path=label)


def test_running_portable_step_stages_manifest_and_stores_output(
    tmp_path: Path,
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> None:
    """A tiny subprocess can read the manifest and write JSON outputs."""
    script_path = tmp_path / "portable_step.py"
    script_path.write_text(
        """
import json
import os

manifest_path = os.environ["ZENML_PORTABLE_STEP_MANIFEST"]
with open(manifest_path, "r", encoding="utf-8") as manifest_file:
    manifest = json.load(manifest_file)

with open(manifest["outputs"]["output"], "w", encoding="utf-8") as output_file:
    json.dump(
        {
            "step_name": manifest["step_name"],
            "parameter": manifest["parameters"]["value"],
            "protocol": manifest["protocol"],
        },
        output_file,
    )
""",
        encoding="utf-8",
    )
    step = _portable_step([sys.executable, str(script_path)], {"value": 7})
    stored_outputs: Dict[str, Any] = {}
    _patch_runner_side_effects(mocker, stored_outputs=stored_outputs)

    runner = PortableStepRunner(step=step, stack=local_stack)
    runner.run(
        pipeline_run=sample_pipeline_run,
        step_run=sample_step_run,
        input_artifacts={},
        output_artifact_uris={"output": str(tmp_path / "artifact")},
        step_run_info=_step_run_info(
            step, sample_step_run, sample_snapshot_response_model
        ),
    )

    assert stored_outputs == {
        "output": {
            "step_name": "portable_step",
            "parameter": 7,
            "protocol": "zenml-portable-json-v1",
        }
    }


@pytest.mark.parametrize(
    ("script", "match"),
    [
        ("", "did not write expected output"),
        (
            'open(manifest["outputs"]["output"], "w").write("{not json")',
            "invalid JSON",
        ),
        (
            'import sys; print("useful stdout"); print("useful stderr", file=sys.stderr); sys.exit(7)',
            "exit code 7",
        ),
    ],
)
def test_portable_step_subprocess_failures_are_clear(
    script: str,
    match: str,
    tmp_path: Path,
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> None:
    """Missing output, invalid JSON, and non-zero exits fail clearly."""
    script_path = tmp_path / "portable_failure.py"
    script_path.write_text(
        """
import json
import os

manifest_path = os.environ["ZENML_PORTABLE_STEP_MANIFEST"]
with open(manifest_path, "r", encoding="utf-8") as manifest_file:
    manifest = json.load(manifest_file)
"""
        + script,
        encoding="utf-8",
    )
    step = _portable_step([sys.executable, str(script_path)])
    _patch_runner_side_effects(mocker)

    runner = PortableStepRunner(step=step, stack=local_stack)
    with pytest.raises(RuntimeError, match=match):
        runner.run(
            pipeline_run=sample_pipeline_run,
            step_run=sample_step_run,
            input_artifacts={},
            output_artifact_uris={"output": str(tmp_path / "artifact")},
            step_run_info=_step_run_info(
                step, sample_step_run, sample_snapshot_response_model
            ),
        )


def test_portable_step_allows_builtin_output_materializers(
    tmp_path: Path,
    local_stack: Stack,
) -> None:
    """The importer-configured built-in materializer path is allowed."""
    step = _portable_step(
        [sys.executable, str(tmp_path / "portable_step.py")],
        output_materializer_source=(
            source_utils.resolve(BuiltInMaterializer),
            source_utils.resolve(BuiltInContainerMaterializer),
        ),
    )

    PortableStepRunner(step=step, stack=local_stack)._validate_step_contract()


def test_portable_step_rejects_custom_output_materializers(
    tmp_path: Path,
    local_stack: Stack,
) -> None:
    """Portable JSON v1 rejects custom output materializers clearly."""
    step = _portable_step(
        [sys.executable, str(tmp_path / "portable_step.py")],
        output_materializer_source=(
            "zenml.materializers.base_materializer.BaseMaterializer",
        ),
    )

    runner = PortableStepRunner(step=step, stack=local_stack)
    with pytest.raises(RuntimeError, match="custom output materializers"):
        runner._validate_step_contract()


def test_portable_step_rejects_heartbeat_for_v1(
    tmp_path: Path,
    local_stack: Stack,
    sample_step_run: StepRunResponse,
) -> None:
    """Heartbeat-enabled portable steps fail with an explicit v1 limit."""
    step = _portable_step(
        [sys.executable, str(tmp_path / "portable_step.py")],
        enable_heartbeat=True,
    )

    runner = PortableStepRunner(step=step, stack=local_stack)
    with pytest.raises(RuntimeError, match="do not support step heartbeat"):
        runner._validate_step_contract()


def test_portable_step_rejects_unsupported_input_json(
    tmp_path: Path,
    mocker: Any,
    local_stack: Stack,
    sample_pipeline_run: PipelineRunResponse,
    sample_step_run: StepRunResponse,
    sample_snapshot_response_model: PipelineSnapshotResponse,
) -> None:
    """Loaded input artifacts must be strict portable JSON before staging."""
    script_path = tmp_path / "portable_step.py"
    script_path.write_text("", encoding="utf-8")
    step = _portable_step([sys.executable, str(script_path)])
    _patch_runner_side_effects(mocker)
    mocker.patch.object(
        StepRunner, "_load_input_artifact", return_value=("not", "json")
    )

    runner = PortableStepRunner(step=step, stack=local_stack)
    with pytest.raises(PortableJSONValueError, match="tuple"):
        runner.run(
            pipeline_run=sample_pipeline_run,
            step_run=sample_step_run,
            input_artifacts={"payload": [MagicMock()]},
            output_artifact_uris={"output": str(tmp_path / "artifact")},
            step_run_info=_step_run_info(
                step, sample_step_run, sample_snapshot_response_model
            ),
        )
