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
"""Runner for ZenBabel portable JSON steps."""

import json
import math
import os
import subprocess
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any, ContextManager, Dict, List

from zenml.config.step_configurations import StepConfiguration
from zenml.config.step_execution_spec import (
    StepExecutionLanguage,
    StepExecutionProtocol,
)
from zenml.config.step_run_info import StepRunInfo
from zenml.deployers.server import runtime
from zenml.hooks.hook_validators import load_and_run_hook
from zenml.logger import get_logger
from zenml.materializers.built_in_materializer import (
    BuiltInContainerMaterializer,
    BuiltInMaterializer,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators.publish_utils import (
    publish_failed_step_run,
    publish_step_run_metadata,
    publish_successful_step_run,
    step_exception_info,
)
from zenml.orchestrators.step_runner import StepRunner
from zenml.orchestrators.utils import is_setting_enabled
from zenml.steps.step_context import StepContext
from zenml.steps.utils import OutputSignature
from zenml.utils import env_utils, exception_utils, source_utils
from zenml.utils.logging_utils import (
    is_step_logging_enabled,
    setup_logging_context,
)
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ZENML_PORTABLE_STEP_MANIFEST = "ZENML_PORTABLE_STEP_MANIFEST"
PORTABLE_JSON_PROTOCOL_VERSION = "zenml-portable-json-v1"
_SUBPROCESS_OUTPUT_LIMIT = 4000
_JAVASCRIPT_MAX_SAFE_INTEGER = 2**53 - 1
_ALLOWED_OUTPUT_MATERIALIZER_SOURCES = {
    source_utils.resolve(BuiltInMaterializer).import_path,
    source_utils.resolve(BuiltInContainerMaterializer).import_path,
}


class PortableJSONValueError(TypeError):
    """Raised when a value is not shaped like strict portable JSON."""


def validate_portable_json_value(value: Any, path: str = "value") -> None:
    """Validate that a value is strict JSON, not merely Python-json-dumpable.

    Args:
        value: The value to validate.
        path: Human-readable path used in error messages.

    Raises:
        PortableJSONValueError: If the value cannot cross the portable JSON
            boundary without changing shape or losing JSON compatibility.
    """
    if value is None or isinstance(value, (str, bool)):
        return

    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > _JAVASCRIPT_MAX_SAFE_INTEGER:
            raise PortableJSONValueError(
                f"Portable JSON value at `{path}` contains integer "
                f"{value!r}, which is outside the JavaScript safe integer "
                "range."
            )
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise PortableJSONValueError(
                f"Portable JSON value at `{path}` contains non-finite float "
                f"{value!r}."
            )
        return

    if isinstance(value, tuple):
        raise PortableJSONValueError(
            f"Portable JSON value at `{path}` is a tuple. Use a list instead."
        )

    if isinstance(value, set):
        raise PortableJSONValueError(
            f"Portable JSON value at `{path}` is a set. Use a list instead."
        )

    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_portable_json_value(item, f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PortableJSONValueError(
                    f"Portable JSON object at `{path}` has non-string key "
                    f"{key!r}."
                )
            validate_portable_json_value(item, f"{path}.{key}")
        return

    raise PortableJSONValueError(
        f"Portable JSON value at `{path}` has unsupported type "
        f"{type(value).__name__}."
    )


class PortableStepRunner:
    """Runs a step body through the portable JSON subprocess protocol."""

    def __init__(self, step: "Step", stack: "Stack") -> None:
        """Initialize the portable step runner.

        Args:
            step: The step to run.
            stack: The stack on which the step should run.
        """
        self._step = step
        self._stack = stack
        self._python_artifact_runner = StepRunner(step=step, stack=stack)

    @property
    def configuration(self) -> StepConfiguration:
        """Configuration of the step to run.

        Returns:
            The step configuration.
        """
        return self._step.config

    def run(
        self,
        pipeline_run: "PipelineRunResponse",
        step_run: "StepRunResponse",
        input_artifacts: Dict[str, List[StepRunInputResponse]],
        output_artifact_uris: Dict[str, str],
        step_run_info: StepRunInfo,
    ) -> None:
        """Run a portable JSON step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            input_artifacts: The input artifact versions of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            step_run_info: The step run info.
        """
        logs_context: ContextManager[Any] = nullcontext()
        if is_step_logging_enabled(
            step_configuration=step_run.config,
            pipeline_configuration=pipeline_run.config,
        ):
            logs_context = setup_logging_context(
                source="step", step_run=step_run, pipeline_run=pipeline_run
            )

        with logs_context:
            self._validate_step_contract()
            output_materializers = (
                self._python_artifact_runner._load_output_materializers()
            )
            output_annotations = self._output_annotations()
            self._python_artifact_runner._evaluate_artifact_names_in_collections(
                step_run,
                output_annotations,
                [output_artifact_uris, output_materializers],
            )

            self._stack.prepare_step_run(info=step_run_info)

            step_context = StepContext(
                pipeline_run=pipeline_run,
                step_run=step_run,
                output_materializers=output_materializers,
                output_artifact_uris=output_artifact_uris,
                output_artifact_configs={
                    name: signature.artifact_config
                    for name, signature in output_annotations.items()
                },
            )

            step_environment = env_utils.get_runtime_environment(
                config=step_run.config, stack=self._stack
            )
            secret_environment = env_utils.get_runtime_secret_environment(
                config=step_run.config, stack=self._stack
            )
            step_environment.update(secret_environment)

            step_failed = False
            output_artifacts = {}

            with step_context:
                try:
                    if (
                        pipeline_run.snapshot
                        and self._stack.orchestrator.run_init_cleanup_at_step_level
                    ):
                        self._stack.orchestrator.run_init_hook(
                            snapshot=pipeline_run.snapshot
                        )

                    output_data = self._execute_portable_step(
                        input_artifacts=input_artifacts,
                        expected_outputs=list(output_annotations),
                        step_environment=step_environment,
                    )

                    if runtime.is_active():
                        runtime.record_step_outputs(step_run.name, output_data)

                    artifact_metadata_enabled = is_setting_enabled(
                        is_enabled_on_step=step_run_info.config.enable_artifact_metadata,
                        is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_metadata,
                    )
                    artifact_visualization_enabled = is_setting_enabled(
                        is_enabled_on_step=step_run_info.config.enable_artifact_visualization,
                        is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_visualization,
                    )
                    output_artifacts = self._python_artifact_runner._store_output_artifacts(
                        output_data=output_data,
                        output_artifact_uris=output_artifact_uris,
                        output_materializers=output_materializers,
                        output_annotations=output_annotations,
                        artifact_metadata_enabled=artifact_metadata_enabled,
                        artifact_visualization_enabled=artifact_visualization_enabled,
                    )

                    if (
                        model_version := step_run.model_version
                        or pipeline_run.model_version
                    ):
                        from zenml.orchestrators import step_run_utils

                        step_run_utils.link_output_artifacts_to_model_version(
                            artifacts={
                                name: [artifact]
                                for name, artifact in output_artifacts.items()
                            },
                            model_version=model_version,
                        )

                except BaseException as step_exception:  # noqa: E722
                    step_failed = True
                    exception_info = (
                        exception_utils.collect_exception_information(
                            step_exception
                        )
                    )
                    step_exception_info.set(exception_info)
                    step_run = publish_failed_step_run(
                        step_run_id=step_run_info.step_run_id
                    )

                    if not step_run.is_retriable:
                        if (
                            failure_hook_source
                            := self.configuration.failure_hook_source
                        ):
                            logger.info("Detected failure hook. Running...")
                            with env_utils.temporary_environment(
                                step_environment
                            ):
                                load_and_run_hook(
                                    failure_hook_source,
                                    step_exception=step_exception,
                                )
                    raise
                finally:
                    step_run_metadata = self._stack.get_step_run_metadata(
                        info=step_run_info,
                    )
                    publish_step_run_metadata(
                        step_run_id=step_run_info.step_run_id,
                        step_run_metadata=step_run_metadata,
                    )
                    self._stack.cleanup_step_run(
                        info=step_run_info, step_failed=step_failed
                    )

                    if not step_failed:
                        if (
                            success_hook_source
                            := self.configuration.success_hook_source
                        ):
                            logger.info("Detected success hook. Running...")
                            with env_utils.temporary_environment(
                                step_environment
                            ):
                                load_and_run_hook(
                                    success_hook_source,
                                    step_exception=None,
                                )

                    if (
                        pipeline_run.snapshot
                        and self._stack.orchestrator.run_init_cleanup_at_step_level
                    ):
                        self._stack.orchestrator.run_cleanup_hook(
                            snapshot=pipeline_run.snapshot
                        )

            output_artifact_ids = {
                output_name: [artifact.id]
                for output_name, artifact in output_artifacts.items()
            }
            publish_successful_step_run(
                step_run_id=step_run_info.step_run_id,
                output_artifact_ids=output_artifact_ids,
            )

    def _validate_step_contract(self) -> None:
        """Validate the portable step execution contract.

        Raises:
            RuntimeError: If the step cannot be executed by this runner.
        """
        execution_spec = self._step.spec.execution_spec
        if execution_spec is None:
            raise RuntimeError(
                "PortableStepRunner requires a step execution spec."
            )

        if (
            execution_spec.protocol
            != StepExecutionProtocol.ZENML_PORTABLE_JSON_V1
        ):
            raise RuntimeError(
                "PortableStepRunner only supports protocol "
                f"`{StepExecutionProtocol.ZENML_PORTABLE_JSON_V1}` but got "
                f"`{execution_spec.protocol}`."
            )

        if execution_spec.language != StepExecutionLanguage.TYPESCRIPT:
            raise RuntimeError(
                "Portable JSON v1 steps currently support only TypeScript "
                f"step bodies, but got `{execution_spec.language}`."
            )

        if self._step.spec.source.import_path != PORTABLE_STEP_ADAPTER_SOURCE:
            raise RuntimeError(
                "Portable JSON v1 steps must use the PortableStepAdapter "
                f"source `{PORTABLE_STEP_ADAPTER_SOURCE}`."
            )

        if self._step.spec.enable_heartbeat:
            raise RuntimeError(
                "Portable JSON v1 steps do not support step heartbeat yet."
            )

        for output_name, output in self.configuration.outputs.items():
            configured_materializers = {
                source.import_path for source in output.materializer_source
            }
            if configured_materializers - _ALLOWED_OUTPUT_MATERIALIZER_SOURCES:
                raise RuntimeError(
                    "Portable JSON v1 steps do not support custom output "
                    "materializers. Outputs must use the default built-in "
                    "JSON-compatible materializer path. Custom materializers "
                    f"were configured for output `{output_name}`."
                )

    def _output_annotations(self) -> Dict[str, OutputSignature]:
        """Build output signatures from the portable step configuration.

        Returns:
            Output signatures keyed by output name.
        """
        return {
            name: OutputSignature(
                resolved_annotation=Any,
                artifact_config=output.artifact_config,
            )
            for name, output in self.configuration.outputs.items()
        }

    def _execute_portable_step(
        self,
        input_artifacts: Dict[str, List[StepRunInputResponse]],
        expected_outputs: List[str],
        step_environment: Dict[str, str],
    ) -> Dict[str, Any]:
        """Execute the child process and collect output JSON values.

        Args:
            input_artifacts: Input artifacts resolved by StepLauncher.
            expected_outputs: Output names expected from the child process.
            step_environment: Environment variables for the child process.

        Returns:
            Output values keyed by output name.
        """
        execution_spec = self._step.spec.execution_spec
        assert execution_spec is not None

        with tempfile.TemporaryDirectory(prefix="zenml-portable-step-") as tmp:
            work_dir = Path(tmp)
            input_paths = self._stage_inputs(
                input_artifacts=input_artifacts, work_dir=work_dir
            )
            output_paths = {
                output_name: str(work_dir / "outputs" / f"output_{index}.json")
                for index, output_name in enumerate(expected_outputs)
            }
            Path(work_dir / "outputs").mkdir(parents=True, exist_ok=True)

            manifest_path = work_dir / "manifest.json"
            manifest = {
                "protocol": PORTABLE_JSON_PROTOCOL_VERSION,
                "step_name": self._step.config.name,
                "source_identity": execution_spec.source_identity,
                "parameters": self._validated_parameters(),
                "inputs": input_paths,
                "outputs": output_paths,
            }
            _write_json_file(manifest_path, manifest)

            env = os.environ.copy()
            env.update(step_environment)
            env[ZENML_PORTABLE_STEP_MANIFEST] = str(manifest_path)

            completed_process = subprocess.run(
                execution_spec.command,
                cwd=str(work_dir),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed_process.stdout:
                logger.info(completed_process.stdout.rstrip())
            if completed_process.stderr:
                logger.warning(completed_process.stderr.rstrip())

            if completed_process.returncode != 0:
                raise RuntimeError(
                    "Portable step subprocess failed with exit code "
                    f"{completed_process.returncode}.\n"
                    f"stdout:\n{_limit_output(completed_process.stdout)}\n"
                    f"stderr:\n{_limit_output(completed_process.stderr)}"
                )

            return self._read_outputs(output_paths)

    def _stage_inputs(
        self,
        input_artifacts: Dict[str, List[StepRunInputResponse]],
        work_dir: Path,
    ) -> Dict[str, str]:
        """Load input artifacts and write portable JSON input files.

        Args:
            input_artifacts: Input artifacts resolved by StepLauncher.
            work_dir: Temporary portable work directory.

        Returns:
            Input JSON file paths keyed by input name.
        """
        input_dir = work_dir / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        input_paths = {}

        for index, (input_name, artifact_list) in enumerate(
            input_artifacts.items()
        ):
            value = self._load_input_value(input_name, artifact_list)
            validate_portable_json_value(value, path=f"input `{input_name}`")
            input_path = input_dir / f"input_{index}.json"
            _write_json_file(input_path, value)
            input_paths[input_name] = str(input_path)

        return input_paths

    def _load_input_value(
        self,
        input_name: str,
        artifact_list: List[StepRunInputResponse],
    ) -> Any:
        """Load a scalar or collection input value.

        Args:
            input_name: The step input name.
            artifact_list: The artifacts connected to the input.

        Returns:
            The materialized input value.
        """
        is_scalar = (
            input_name not in self._step.spec.inputs
            or self._step.spec.is_scalar_input(input_name)
        )
        if is_scalar:
            if len(artifact_list) != 1:
                raise RuntimeError(
                    f"Expected a single artifact for portable input "
                    f"`{input_name}`."
                )
            return self._python_artifact_runner._load_input_artifact(
                artifact_list[0], data_type=Any
            )

        return [
            self._python_artifact_runner._load_input_artifact(
                artifact, data_type=Any
            )
            for artifact in artifact_list
        ]

    def _validated_parameters(self) -> Dict[str, Any]:
        """Validate and return portable step parameters.

        Returns:
            The JSON-compatible parameter mapping.
        """
        parameters = dict(self.configuration.parameters)
        validate_portable_json_value(parameters, path="parameters")
        return parameters

    def _read_outputs(self, output_paths: Dict[str, str]) -> Dict[str, Any]:
        """Read and validate child-process output JSON files.

        Args:
            output_paths: Expected output file paths keyed by output name.

        Returns:
            Output values keyed by output name.
        """
        output_data = {}
        for output_name, output_path in output_paths.items():
            path = Path(output_path)
            if not path.exists():
                raise RuntimeError(
                    f"Portable step did not write expected output "
                    f"`{output_name}` to `{output_path}`."
                )

            try:
                with path.open("r", encoding="utf-8") as file:
                    value = json.load(
                        file, parse_constant=_reject_json_constant
                    )
            except (json.JSONDecodeError, ValueError) as e:
                raise RuntimeError(
                    f"Portable step wrote invalid JSON for output "
                    f"`{output_name}` at `{output_path}`: {e}"
                ) from e

            validate_portable_json_value(value, path=f"output `{output_name}`")
            output_data[output_name] = value

        return output_data


def _write_json_file(path: Path, value: Any) -> None:
    """Write strict JSON to a file.

    Args:
        path: The file to write.
        value: The JSON-compatible value to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, allow_nan=False, sort_keys=True)


def _reject_json_constant(value: str) -> None:
    """Reject JSON constants accepted by Python but invalid in strict JSON.

    Args:
        value: The invalid constant.

    Raises:
        ValueError: Always, because the value is not strict JSON.
    """
    raise ValueError(f"Invalid JSON constant `{value}`.")


def _limit_output(output: str) -> str:
    """Limit subprocess output included in exceptions.

    Args:
        output: The subprocess output.

    Returns:
        The output, truncated from the front if necessary.
    """
    if len(output) <= _SUBPROCESS_OUTPUT_LIMIT:
        return output

    return "..." + output[-_SUBPROCESS_OUTPUT_LIMIT:]
