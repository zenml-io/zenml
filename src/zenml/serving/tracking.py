#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Pipeline run and artifact tracking for served pipelines."""

# Removed random import - now using deterministic sampling
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from zenml.artifacts.utils import save_artifact
from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.serving.capture import (
    Capture,
    EffectiveCapture,
    ValueCapturePlan,
    overlay_capture,
    should_capture_value_artifacts,
    should_capture_value_payload,
)
from zenml.serving.events import EventType, ServingEvent
from zenml.serving.policy import (
    CapturePolicy,
    CapturePolicyMode,
    redact_fields,
    should_capture_payloads,
    truncate_payload,
)
from zenml.utils import string_utils
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)


class TrackingManager:
    """Manages pipeline run and artifact tracking for served pipelines."""

    def __init__(
        self,
        deployment: PipelineDeploymentResponse,
        policy: CapturePolicy,
        create_runs: bool = True,
        invocation_id: Optional[str] = None,
    ) -> None:
        """Initialize the tracking manager.

        Args:
            deployment: Pipeline deployment being served
            policy: Effective capture policy for this invocation
            create_runs: Whether to create pipeline/step runs
            invocation_id: Unique invocation ID for this execution
        """
        self.deployment = deployment
        self.policy = policy
        self.create_runs = create_runs
        self.invocation_id = (
            invocation_id or f"serving-{int(time.time() * 1000)}"
        )

        # Initialize client for store operations (will be created per-thread)
        self._client: Optional[Client] = None

        # Track current run state
        self.pipeline_run: Optional[PipelineRunResponse] = None
        self.step_runs: Dict[str, StepRunResponse] = {}
        self.start_time: Optional[float] = None
        self.step_timings: Dict[str, Dict[str, float]] = {}

        # Track finalized steps to prevent double completion
        self._finalized_steps: set[str] = set()

        # Storage for step-level capture overrides
        self._step_capture_overrides: Dict[
            str, Dict[str, Dict[str, Optional[Capture]]]
        ] = {}

        # Storage for pipeline-level per-value capture overrides
        self._pipeline_capture_overrides: Dict[str, Dict[str, Capture]] = {
            "inputs": {},
            "outputs": {},
        }

        # Storage for step-level global mode overrides
        self._step_mode_overrides: Dict[str, str] = {}

        # Immutable capture plans computed once and reused
        self._capture_plans: Dict[str, ValueCapturePlan] = {}

        # Observability counters for auditing capture behavior
        self._capture_counters = {
            "previews_saved_inputs": 0,
            "previews_saved_outputs": 0,
            "artifacts_saved_count": 0,
        }

        # Determine if this invocation should be sampled
        self.is_sampled = self._should_sample()

    @property
    def client(self) -> Client:
        """Get thread-safe client instance."""
        client = self._client
        if client is None:
            client = Client()
            self._client = client
        return client

    def _should_sample(self) -> bool:
        """Determine if this invocation should be sampled for full capture.

        Uses deterministic sampling based on invocation_id to ensure consistent
        behavior across multiple calls with the same ID.
        """
        if self.policy.mode not in [CapturePolicyMode.SAMPLED]:
            return False
        return self._is_sampled(self.invocation_id, self.policy.sample_rate)

    def _is_sampled(self, key: str, rate: float) -> bool:
        """Deterministic sampling based on stable hash of invocation key.

        IMPORTANT: This is invocation-level sampling only. All per-value decisions
        within the same invocation use the same base sampling result to avoid
        "partial" behavior where some values are captured but others aren't.

        Args:
            key: Unique key for this invocation (job_id)
            rate: Sampling rate [0.0, 1.0], clamped to valid range

        Returns:
            True if this invocation should be sampled based on the rate
        """
        # Clamp rate to valid range
        rate = max(0.0, min(1.0, rate))

        if rate <= 0.0:
            return False
        if rate >= 1.0:
            return True

        import hashlib

        # Use SHA1 hash for stable, uniform distribution
        hash_bytes = hashlib.sha1(key.encode("utf-8")).digest()[:4]
        # Convert first 4 bytes to int, normalize to [0, 1) with guaranteed precision
        hash_val = int.from_bytes(hash_bytes, "big") / (2**32)
        return hash_val < rate

    def set_step_capture_overrides(
        self, overrides: Dict[str, Dict[str, Dict[str, Optional[Capture]]]]
    ) -> None:
        """Set step-level capture overrides from annotation parsing.

        Args:
            overrides: Mapping of step_name -> {"inputs": {...}, "outputs": {...}}
        """
        self._step_capture_overrides = overrides
        # Build immutable capture plans immediately
        self._build_capture_plans()

    def set_pipeline_capture_overrides(
        self, overrides: Dict[str, Union[str, Dict[str, str]]]
    ) -> None:
        """Set pipeline-level per-value capture overrides.

        Args:
            overrides: Dict with "inputs" and/or "outputs" keys mapping to mode strings
                      or dicts of {param_name: mode_string}
        """
        from zenml.serving.capture import Capture

        normalized_overrides: Dict[str, Dict[str, Capture]] = {
            "inputs": {},
            "outputs": {},
        }

        # Process inputs
        if "inputs" in overrides:
            inputs_config = overrides["inputs"]
            if isinstance(inputs_config, dict):
                for param_name, mode in inputs_config.items():
                    normalized_overrides["inputs"][param_name] = Capture(
                        mode=mode
                    )

        # Process outputs
        if "outputs" in overrides:
            outputs_config = overrides["outputs"]
            if isinstance(outputs_config, str):
                # Single mode for default output
                normalized_overrides["outputs"]["output"] = Capture(
                    mode=outputs_config
                )
            elif isinstance(outputs_config, dict):
                for output_name, mode in outputs_config.items():
                    normalized_overrides["outputs"][output_name] = Capture(
                        mode=mode
                    )

        self._pipeline_capture_overrides = normalized_overrides
        # Rebuild capture plans to include pipeline overrides
        self._build_capture_plans()

    def set_step_mode_overrides(
        self, step_mode_overrides: Dict[str, str]
    ) -> None:
        """Set step-level global mode overrides.

        Args:
            step_mode_overrides: Dict mapping step names to their mode overrides
        """
        self._step_mode_overrides = step_mode_overrides

    def _get_effective_policy_for_step(self, step_name: str) -> CapturePolicy:
        """Get the effective capture policy for a specific step.

        Considers step-level global mode override if present.

        Args:
            step_name: Name of the step

        Returns:
            Effective capture policy for the step
        """
        if step_name in self._step_mode_overrides:
            from zenml.serving.policy import (
                CapturePolicyMode,
                derive_artifacts_from_mode,
            )

            # Create step-specific policy with mode override
            step_mode = CapturePolicyMode(self._step_mode_overrides[step_name])
            return CapturePolicy(
                mode=step_mode,
                artifacts=derive_artifacts_from_mode(step_mode),
                sample_rate=self.policy.sample_rate,
                max_bytes=self.policy.max_bytes,
                redact=self.policy.redact,
                retention_days=self.policy.retention_days,
            )

        return self.policy

    def _build_capture_plans(self) -> None:
        """Build immutable capture plans for all steps with proper precedence.

        Precedence: Step > Pipeline > Annotation > Base policy
        """
        for step_name, step_overrides in self._step_capture_overrides.items():
            # Get step-specific base policy (considers step-level global mode)
            base_policy = self._get_effective_policy_for_step(step_name)

            input_configs = {}
            for param_name, capture_annotation in step_overrides.get(
                "inputs", {}
            ).items():
                # Step-level override takes highest precedence
                effective = overlay_capture(base_policy, capture_annotation)
                input_configs[param_name] = effective

            output_configs = {}
            for output_name, capture_annotation in step_overrides.get(
                "outputs", {}
            ).items():
                # Step-level override takes highest precedence
                effective = overlay_capture(base_policy, capture_annotation)
                output_configs[output_name] = effective

            self._capture_plans[step_name] = ValueCapturePlan(
                step_name=step_name,
                inputs=input_configs,
                outputs=output_configs,
            )

    def _get_effective_capture_for_value(
        self,
        step_name: str,
        value_name: str,
        value_type: str,  # "input" or "output"
    ) -> EffectiveCapture:
        """Get effective capture configuration for a specific input or output value.

        Implements precedence: Step > Pipeline > Annotation > Base policy

        Args:
            step_name: Name of the step
            value_name: Name of the input parameter or output
            value_type: Either "input" or "output"

        Returns:
            Effective capture configuration with proper precedence
        """
        # 1. Step-level override (highest priority)
        if step_name in self._capture_plans:
            plan = self._capture_plans[step_name]
            if value_type == "input" and value_name in plan.inputs:
                return plan.inputs[value_name]
            elif value_type == "output" and value_name in plan.outputs:
                return plan.outputs[value_name]

        # 2. Pipeline-level per-value override
        pipeline_override = None
        if value_type in self._pipeline_capture_overrides:
            value_overrides = self._pipeline_capture_overrides[value_type]
            if value_name in value_overrides:
                pipeline_override = value_overrides[value_name]

        # 3. Annotation-level (handled in step parsing, will be None here for pipeline-only values)
        # 4. Base policy (lowest priority, but use step-specific policy if step has mode override)

        # Use step-specific base policy if step has mode override
        base_policy = self._get_effective_policy_for_step(step_name)
        return overlay_capture(base_policy, pipeline_override)

    def start_pipeline(
        self,
        run_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[UUID]:
        """Start tracking a pipeline run.

        Args:
            run_name: Optional custom run name
            params: Pipeline parameters for this execution

        Returns:
            Pipeline run ID if created, None otherwise
        """
        if not self.create_runs or self.policy.mode == CapturePolicyMode.NONE:
            return None

        try:
            self.start_time = time.time()

            # Generate run name if not provided
            if not run_name:
                timestamp = utc_now()
                run_name = string_utils.format_name_template(
                    name_template=self.deployment.run_name_template,
                    substitutions=self.deployment.pipeline_configuration.finalize_substitutions(
                        start_time=timestamp,
                    ),
                )

            # Prepare metadata
            metadata: Dict[str, MetadataType] = {
                "serving_invocation_id": self.invocation_id,
                "endpoint_id": str(self.deployment.id),
                "capture_mode": str(self.policy.mode),
                "is_sampled": self.is_sampled,
            }

            # Add parameter metadata with per-parameter capture control
            if params:
                captured_params = {}
                for param_name, param_value in params.items():
                    # Check if any step has an input annotation for this parameter
                    should_capture_param = False
                    effective_capture = None

                    # Find the most restrictive capture setting for this parameter across all steps
                    for step_name in self._step_capture_overrides:
                        input_overrides = self._step_capture_overrides[
                            step_name
                        ].get("inputs", {})
                        if (
                            param_name in input_overrides
                            and input_overrides[param_name] is not None
                        ):
                            effective_capture = (
                                self._get_effective_capture_for_value(
                                    step_name, param_name, "input"
                                )
                            )
                            should_capture_param = (
                                should_capture_value_payload(
                                    effective_capture, self.is_sampled
                                )
                            )
                            break

                    # Fall back to global policy if no step-specific annotation
                    if effective_capture is None:
                        effective_capture = overlay_capture(self.policy, None)
                        should_capture_param = should_capture_payloads(
                            self.policy, self.is_sampled
                        )

                    if should_capture_param:
                        redacted_value = redact_fields(
                            {param_name: param_value}, effective_capture.redact
                        )[param_name]
                        captured_params[param_name] = redacted_value
                        self._capture_counters["previews_saved_inputs"] += 1

                if captured_params:
                    metadata["parameters_preview"] = truncate_payload(
                        captured_params, self.policy.max_bytes
                    )

            run_request = PipelineRunRequest(
                name=run_name,
                project=self.deployment.project_id,
                deployment=self.deployment.id,
                pipeline=self.deployment.pipeline.id
                if self.deployment.pipeline
                else None,
                orchestrator_run_id=self.invocation_id,
                status=ExecutionStatus.RUNNING,
                start_time=utc_now(),
                tags=self.deployment.pipeline_configuration.tags,
                # Removed config=metadata - metadata should be logged separately
            )

            self.pipeline_run, _ = self.client.zen_store.get_or_create_run(
                run_request
            )

            # Log initial metadata separately after run creation
            from zenml.utils.metadata_utils import log_metadata

            try:
                log_metadata(
                    metadata=metadata,
                    run_id_name_or_prefix=self.pipeline_run.id,
                )
            except Exception as e:
                logger.warning(f"Failed to log initial run metadata: {e}")

            logger.info(
                f"Created pipeline run: {self.pipeline_run.name} ({self.pipeline_run.id})"
            )

            return self.pipeline_run.id

        except Exception as e:
            logger.warning(f"Failed to create pipeline run: {e}")
            return None

    def complete_pipeline(
        self,
        success: bool = True,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
        steps_executed: int = 0,
        results: Optional[Any] = None,
    ) -> None:
        """Complete pipeline run tracking.

        Args:
            success: Whether pipeline execution was successful
            error: Error message if execution failed
            execution_time: Total execution time in seconds
            steps_executed: Number of steps that were executed
            results: Pipeline execution results (optional)
        """
        if not self.pipeline_run:
            return

        try:
            status = (
                ExecutionStatus.COMPLETED
                if success
                else ExecutionStatus.FAILED
            )
            end_time = utc_now()

            # Build fresh metadata with execution summary (ensure MetadataType compliance)
            metadata: Dict[str, MetadataType] = {
                "steps_executed": steps_executed,
                # Convert step_timings to primitive values for MetadataType compliance
                "step_timings": {
                    step_name: {
                        "start": float(timings.get("start", 0)),
                        "end": float(timings.get("end", 0)),
                        "duration": float(timings.get("duration", 0)),
                    }
                    for step_name, timings in self.step_timings.items()
                },
                # Observability counters for auditing capture behavior
                "previews_saved_inputs": self._capture_counters[
                    "previews_saved_inputs"
                ],
                "previews_saved_outputs": self._capture_counters[
                    "previews_saved_outputs"
                ],
                "artifacts_saved_count": self._capture_counters[
                    "artifacts_saved_count"
                ],
            }

            if execution_time is not None:
                metadata["execution_time_seconds"] = execution_time

            if error:
                metadata["error_message"] = str(error)[
                    :1000
                ]  # Truncate long errors

            # Add results preview if policy allows and successful
            if (
                success
                and results
                and should_capture_payloads(self.policy, self.is_sampled)
            ):
                redacted_results = redact_fields(
                    results
                    if isinstance(results, dict)
                    else {"result": results},
                    self.policy.redact,
                )
                metadata["results_preview"] = truncate_payload(
                    redacted_results, self.policy.max_bytes
                )

            # Update the run status using the correct ZenML store API
            run_update = PipelineRunUpdate(
                status=status,
                end_time=end_time,
            )

            self.client.zen_store.update_run(
                run_id=self.pipeline_run.id,
                run_update=run_update,
            )

            # Store metadata separately using ZenML metadata utility
            from zenml.utils.metadata_utils import log_metadata

            try:
                log_metadata(
                    metadata=metadata,
                    run_id_name_or_prefix=self.pipeline_run.id,
                )
            except Exception as e:
                logger.warning(f"Failed to log run metadata: {e}")

            logger.info(
                f"Pipeline run completed: {self.pipeline_run.name} "
                f"(status={status.value}, steps={steps_executed})"
            )

        except Exception as e:
            logger.warning(f"Failed to update pipeline run status: {e}")

    def start_step(
        self,
        step_name: str,
        step_config: Optional[Step] = None,
    ) -> Optional[UUID]:
        """Start tracking a step run.

        Args:
            step_name: Name of the step being executed
            step_config: Step configuration if available

        Returns:
            Step run ID if created, None otherwise
        """
        if not self.pipeline_run:
            return None

        try:
            self.step_timings[step_name] = {"start": time.time()}

            step_request = StepRunRequest(
                name=step_name,
                pipeline_run_id=self.pipeline_run.id,
                status=ExecutionStatus.RUNNING,
                start_time=utc_now(),
                project=self.client.active_project.id,
            )

            step_run = self.client.zen_store.create_run_step(step_request)
            self.step_runs[step_name] = step_run

            logger.debug(f"Created step run: {step_name} ({step_run.id})")
            return step_run.id

        except Exception as e:
            logger.warning(f"Failed to create step run for {step_name}: {e}")
            return None

    def complete_step(
        self,
        step_name: str,
        output: Any,
        step_config: Optional[Step] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Complete step run tracking with output artifacts.

        Args:
            step_name: Name of the completed step
            output: Step output data
            step_config: Step configuration if available
            success: Whether step execution was successful
            error: Error message if step failed
        """
        step_run = self.step_runs.get(step_name)
        if not step_run:
            return

        # Guard against double finalization
        if step_name in self._finalized_steps:
            logger.debug(f"Step {step_name} already finalized, skipping")
            return

        self._finalized_steps.add(step_name)

        try:
            # Record timing
            if step_name in self.step_timings:
                self.step_timings[step_name]["end"] = time.time()
                self.step_timings[step_name]["duration"] = (
                    self.step_timings[step_name]["end"]
                    - self.step_timings[step_name]["start"]
                )

            status = (
                ExecutionStatus.COMPLETED
                if success
                else ExecutionStatus.FAILED
            )
            end_time = utc_now()

            # Prepare step metadata
            metadata: Dict[str, MetadataType] = {}
            if error:
                metadata["error_message"] = str(error)[:1000]

            # Handle artifacts with per-output capture control
            outputs_map = {}
            if output is not None:
                if isinstance(output, dict):
                    # Handle multiple named outputs
                    for output_name, output_value in output.items():
                        effective_capture = (
                            self._get_effective_capture_for_value(
                                step_name, output_name, "output"
                            )
                        )
                        should_persist = should_capture_value_artifacts(
                            effective_capture,
                            is_error=not success,
                            is_sampled=self.is_sampled,
                        )
                        if should_persist:
                            single_output_map = self._persist_step_outputs(
                                step_name=step_name,
                                output={output_name: output_value},
                                step_config=step_config,
                                is_error=not success,
                                output_name=output_name,
                            )
                            outputs_map.update(single_output_map)
                else:
                    # Handle single output
                    effective_capture = self._get_effective_capture_for_value(
                        step_name, "output", "output"
                    )
                    should_persist = should_capture_value_artifacts(
                        effective_capture,
                        is_error=not success,
                        is_sampled=self.is_sampled,
                    )
                    if should_persist:
                        outputs_map = self._persist_step_outputs(
                            step_name=step_name,
                            output=output,
                            step_config=step_config,
                            is_error=not success,
                        )

            # Add output preview to metadata with per-output capture control
            if success and output is not None:
                captured_outputs = {}

                if isinstance(output, dict):
                    # Handle multiple named outputs
                    for output_name, output_value in output.items():
                        effective_capture = (
                            self._get_effective_capture_for_value(
                                step_name, output_name, "output"
                            )
                        )
                        should_capture_preview = should_capture_value_payload(
                            effective_capture, self.is_sampled
                        )
                        if should_capture_preview:
                            redacted_value = redact_fields(
                                {output_name: output_value},
                                effective_capture.redact,
                            )[output_name]
                            captured_outputs[output_name] = redacted_value
                            self._capture_counters[
                                "previews_saved_outputs"
                            ] += 1
                else:
                    # Handle single output
                    effective_capture = self._get_effective_capture_for_value(
                        step_name, "output", "output"
                    )
                    should_capture_preview = should_capture_value_payload(
                        effective_capture, self.is_sampled
                    )
                    if should_capture_preview:
                        redacted_output = redact_fields(
                            {"output": output}, effective_capture.redact
                        )["output"]
                        captured_outputs["output"] = redacted_output
                        self._capture_counters["previews_saved_outputs"] += 1

                if captured_outputs:
                    metadata["output_preview"] = truncate_payload(
                        captured_outputs, self.policy.max_bytes
                    )

            # Update the step run using proper StepRunUpdate model
            # Convert outputs_map to correct format: Dict[str, List[UUID]]
            from uuid import UUID

            formatted_outputs: Dict[str, List[UUID]] = {}
            for output_name, artifact_id in outputs_map.items():
                # Handle case where artifact_id might already be a UUID
                if isinstance(artifact_id, UUID):
                    formatted_outputs[output_name] = [artifact_id]
                else:
                    formatted_outputs[output_name] = [UUID(artifact_id)]

            step_update = StepRunUpdate(
                status=status,
                end_time=end_time,
                outputs=formatted_outputs,
            )

            self.client.zen_store.update_run_step(
                step_run_id=step_run.id,
                step_run_update=step_update,
            )

            # Store metadata separately using ZenML metadata utility
            from zenml.utils.metadata_utils import log_metadata

            try:
                log_metadata(metadata=metadata, step_id=step_run.id)
            except Exception as e:
                logger.warning(f"Failed to log step metadata: {e}")

            logger.debug(
                f"Step run completed: {step_name} "
                f"(status={status.value}, artifacts={len(outputs_map)})"
            )

        except Exception as e:
            logger.warning(f"Failed to update step run {step_name}: {e}")

    def _persist_step_outputs(
        self,
        step_name: str,
        output: Any,
        step_config: Optional[Step] = None,
        is_error: bool = False,
        output_name: Optional[str] = None,
    ) -> Dict[str, Union[str, UUID]]:
        """Persist step outputs as artifacts and return outputs mapping.

        Args:
            step_name: Name of the step
            output: Step output data
            step_config: Step configuration for materializer resolution
            is_error: Whether this is for a failed step
            output_name: Specific output name when handling named outputs

        Returns:
            Dictionary mapping output names to artifact version IDs
        """
        outputs_map: Dict[str, Union[str, UUID]] = {}

        try:
            # Note: Persistence decision is now made by caller using per-value capture logic
            # This method just handles the actual artifact creation

            # Resolve materializers if step config is available
            materializers: Dict[str, Any] = {}
            if step_config and hasattr(
                step_config.config, "output_materializers"
            ):
                output_materializers = getattr(
                    step_config.config, "output_materializers", {}
                )
                if output_materializers:
                    materializers = output_materializers

            # Handle different output types
            if isinstance(output, dict):
                # Multiple named outputs
                for output_name, output_value in output.items():
                    # output_name from dict.items() is guaranteed to be str, not None
                    assert output_name is not None
                    artifact_name = f"{step_name}::{output_name}"
                    if is_error:
                        artifact_name += "::error"

                    try:
                        # Try to get specific materializer for this output
                        specific_materializer = materializers.get(output_name)

                        artifact_version = save_artifact(
                            data=output_value,
                            name=artifact_name,
                            version=None,  # Auto-generate version
                            tags=[
                                f"serving_step:{step_name}",
                                f"invocation:{self.invocation_id}",
                            ],
                            materializer=specific_materializer,
                        )
                        outputs_map[output_name] = str(artifact_version.id)
                        self._capture_counters["artifacts_saved_count"] += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to save artifact {artifact_name}: {e}"
                        )
            else:
                # Single output
                artifact_name = f"{step_name}::output"
                if is_error:
                    artifact_name += "::error"

                try:
                    # Try to get materializer for single output
                    single_materializer = materializers.get("output") or (
                        list(materializers.values())[0]
                        if materializers
                        else None
                    )

                    artifact_version = save_artifact(
                        data=output,
                        name=artifact_name,
                        version=None,
                        tags=[
                            f"serving_step:{step_name}",
                            f"invocation:{self.invocation_id}",
                        ],
                        materializer=single_materializer,
                    )
                    outputs_map["output"] = str(artifact_version.id)
                    self._capture_counters["artifacts_saved_count"] += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to save artifact {artifact_name}: {e}"
                    )

        except Exception as e:
            logger.warning(
                f"Failed to persist outputs for step {step_name}: {e}"
            )

        return outputs_map

    def handle_event(self, event: ServingEvent) -> None:
        """Handle streaming events for tracking purposes.

        Args:
            event: Streaming event from pipeline execution
        """
        if not self.create_runs or self.policy.mode == CapturePolicyMode.NONE:
            return

        event_type = event.event_type
        step_name = event.step_name

        try:
            if event_type == EventType.PIPELINE_STARTED:
                # Pipeline start is handled explicitly in start_pipeline
                pass
            elif event_type == EventType.STEP_STARTED and step_name:
                self.start_step(step_name)
            elif event_type == EventType.STEP_COMPLETED and step_name:
                # Note: step completion is now handled primarily by result_callback
                # This is kept for backward compatibility but should be a no-op
                # if result_callback is also handling the same step
                pass
            elif event_type == EventType.STEP_FAILED and step_name:
                # Note: step failure is now handled primarily by result_callback
                # This is kept for backward compatibility but should be a no-op
                # if result_callback is also handling the same step
                pass
            elif event_type in [
                EventType.PIPELINE_COMPLETED,
                EventType.PIPELINE_FAILED,
            ]:
                # IMPORTANT: Pipeline completion is strictly single-source from service.py
                # after engine.execute() returns. TrackingManager must ignore these events
                # to prevent double finalization and ensure exact timing/exception context.
                logger.debug(f"Ignoring {event_type} - handled by service.py")
                return
        except Exception as e:
            logger.warning(
                f"Failed to handle tracking event {event_type}: {e}"
            )

    def handle_step_result(
        self,
        step_name: str,
        output: Any,
        success: bool,
        step_config: Optional[Step] = None,
    ) -> None:
        """Handle raw step results for artifact and payload capture.

        This method is called directly by the engine with the raw Python output,
        enabling artifact persistence and payload capture without serialization loss.

        Args:
            step_name: Name of the step that produced the result
            output: Raw Python output from the step
            success: Whether the step execution was successful
            step_config: Step configuration if available
        """
        if not self.create_runs or self.policy.mode == CapturePolicyMode.NONE:
            return

        try:
            if success:
                self.complete_step(
                    step_name=step_name,
                    output=output,
                    step_config=step_config,
                    success=True,
                )
            else:
                self.complete_step(
                    step_name=step_name,
                    output=output,
                    step_config=step_config,
                    success=False,
                    error="Step execution failed",
                )
        except Exception as e:
            logger.warning(
                f"Failed to handle step result for {step_name}: {e}"
            )
