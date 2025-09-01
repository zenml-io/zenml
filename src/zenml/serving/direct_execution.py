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
"""Direct execution engine for ZenML pipeline serving.

This module provides a direct execution engine that bypasses orchestrators,
artifact stores, and caching mechanisms for ultra-fast pipeline execution
in serving scenarios.
"""

import asyncio
import inspect
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

from zenml.logger import get_logger
from zenml.orchestrators.topsort import topsorted_layers
from zenml.serving.capture import Capture
from zenml.serving.context import serving_job_context, serving_step_context
from zenml.serving.events import EventBuilder, ServingEvent
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)


class CancellationToken(Protocol):
    """Protocol for cancellation tokens that support is_set() check."""

    def is_set(self) -> bool:
        """Check if cancellation has been requested."""
        ...


# ServingStepContext has been moved to zenml.serving.context
# This class is now deprecated and will be removed


class DirectExecutionEngine:
    """Direct pipeline execution engine optimized for serving.

    This engine executes ZenML pipelines directly without using orchestrators,
    artifact stores, or caching. It's designed for real-time serving scenarios
    where low latency is critical.

    Key features:
    - Pre-loads all step instances during initialization
    - Passes data directly between steps without serialization
    - No database operations during execution
    - Maintains compatibility with existing step implementations
    """

    def __init__(
        self,
        deployment: "PipelineDeploymentResponse",
        pipeline_run: Optional[Any] = None,
        event_callback: Optional[Callable[[ServingEvent], None]] = None,
        result_callback: Optional[Callable[[str, Any, bool], None]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ):
        """Initialize the direct execution engine.

        Args:
            deployment: The pipeline deployment configuration
            pipeline_run: Optional pipeline run for tracking. If provided,
                steps will have proper context with run information.
            event_callback: Optional callback for sending events during execution
            result_callback: Optional callback for raw step results (step_name, output, success)
            cancellation_token: Optional token to check for cancellation requests
        """
        self.deployment = deployment
        self.pipeline_run = pipeline_run
        self.event_callback = event_callback
        self.result_callback = result_callback
        self.cancellation_token = cancellation_token
        self._loaded_steps: Dict[str, type] = {}
        self._execution_order: List[str] = []
        self._step_capture_overrides: Dict[
            str, Dict[str, Dict[str, Optional[Capture]]]
        ] = {}
        self._step_mode_overrides: Dict[str, str] = {}

        # Pre-load all steps and build execution order
        self._initialize_steps()
        self._build_execution_order()

        logger.debug(
            f"DirectExecutionEngine initialized for pipeline "
            f"'{deployment.pipeline_configuration.name}' with "
            f"{len(self._loaded_steps)} steps"
            f"{' (tracked)' if pipeline_run else ' (untracked)'}"
            f"{' (with events)' if event_callback else ''}"
            f"{' (cancellable)' if cancellation_token else ''}"
        )

    def get_step_mode_overrides(self) -> Dict[str, str]:
        """Get step-level global mode overrides.

        Returns:
            Dict mapping step names to their mode overrides
        """
        return self._step_mode_overrides.copy()

    def _initialize_steps(self) -> None:
        """Pre-load all step instances for fast execution.

        This method loads step classes and creates instances during
        initialization to avoid loading overhead during request handling.

        TODO (Post-MVP): Implement resource pooling and initialization modes
        ====================================================================

        Future enhancements for production:

        1. Resource Pooling:
           - Create a global StepResourcePool to share step instances
           - Use weak references for automatic garbage collection
           - Implement LRU eviction for memory management

        2. Initialization Modes:
           - Add @init_step decorator for steps that should run during FastAPI startup
           - Support global model loading: models loaded once, shared across requests
           - Example:
             @init_step
             def load_llm_model() -> LLMModel:
                 return load_large_model()  # Runs once at startup

             @step
             def predict(text: str, model: LLMModel) -> str:
                 return model.predict(text)  # Uses pre-loaded model

        3. Lazy Loading:
           - Load steps on first use rather than all at startup
           - Faster service startup time
           - Lower memory usage for rarely used steps
        """
        for (
            step_name,
            step_config,
        ) in self.deployment.step_configurations.items():
            try:
                # Load the step class from its source
                step_source = step_config.spec.source
                logger.debug(
                    f"Loading step '{step_name}' from source: {step_source}"
                )

                # Use source_utils to load the step class
                step_class = source_utils.load(step_source)

                # Store the step class (don't instantiate yet)
                # We'll instantiate it during execution with proper parameters
                self._loaded_steps[step_name] = step_class

                # Parse capture annotations for this step
                self._parse_step_capture_annotations(step_name, step_class)

                logger.debug(f"Successfully loaded step '{step_name}'")

            except Exception as e:
                logger.error(f"Failed to load step '{step_name}': {str(e)}")
                raise RuntimeError(
                    f"Failed to initialize step '{step_name}': {str(e)}"
                ) from e

    def _parse_step_capture_annotations(
        self, step_name: str, step_class: type
    ) -> None:
        """Parse capture configuration from step settings.

        Args:
            step_name: Name of the step
            step_class: Loaded step class
        """
        try:
            # Get step configuration
            step_config = self.deployment.step_configurations.get(step_name)
            if not step_config:
                logger.debug(f"No step configuration found for '{step_name}'")
                self._step_capture_overrides[step_name] = {
                    "inputs": {},
                    "outputs": {},
                }
                return

            # Check for serving capture configuration in step settings
            step_settings = step_config.config.settings

            # First check for new serving_capture format
            from zenml.utils.settings_utils import (
                get_step_serving_capture_settings,
            )

            step_capture_settings = get_step_serving_capture_settings(
                step_settings
            )
            capture_config: Dict[str, Any] = {}

            if step_capture_settings:
                # Parse step-level global mode if present
                if (
                    step_capture_settings.mode
                    and step_capture_settings.mode != "full"
                ):
                    self._step_mode_overrides[
                        step_name
                    ] = step_capture_settings.mode

                # Convert new format to legacy format for processing
                if step_capture_settings.inputs:
                    capture_config["inputs"] = {}
                    for (
                        param_name,
                        mode,
                    ) in step_capture_settings.inputs.items():
                        capture_config["inputs"][param_name] = {"mode": mode}

                if step_capture_settings.outputs:
                    capture_config["outputs"] = {}
                    if isinstance(step_capture_settings.outputs, str):
                        # Single mode for default output
                        capture_config["outputs"]["output"] = {
                            "mode": step_capture_settings.outputs
                        }
                    elif isinstance(step_capture_settings.outputs, dict):
                        for (
                            output_name,
                            mode,
                        ) in step_capture_settings.outputs.items():
                            capture_config["outputs"][output_name] = {
                                "mode": mode
                            }

                # Add global settings if available
                if step_capture_settings.max_bytes is not None:
                    for section in ["inputs", "outputs"]:
                        if section in capture_config:
                            for param_config in capture_config[
                                section
                            ].values():
                                param_config[
                                    "max_bytes"
                                ] = step_capture_settings.max_bytes

                if step_capture_settings.redact is not None:
                    for section in ["inputs", "outputs"]:
                        if section in capture_config:
                            for param_config in capture_config[
                                section
                            ].values():
                                param_config[
                                    "redact"
                                ] = step_capture_settings.redact
            else:
                # Fallback to legacy serving.capture format
                serving_settings = step_settings.get("serving")

                # If serving_settings is a BaseSettings object, convert to dict
                if serving_settings is not None and hasattr(
                    serving_settings, "model_dump"
                ):
                    serving_dict = serving_settings.model_dump()
                elif isinstance(serving_settings, dict):
                    serving_dict = serving_settings
                else:
                    serving_dict = {}

                capture_config = serving_dict.get("capture", {})

                # Parse step-level global mode from legacy format if present
                if (
                    "mode" in capture_config
                    and capture_config["mode"] != "full"
                ):
                    self._step_mode_overrides[step_name] = capture_config[
                        "mode"
                    ]

            if not capture_config:
                logger.debug(
                    f"No capture configuration found in step '{step_name}' settings"
                )
                self._step_capture_overrides[step_name] = {
                    "inputs": {},
                    "outputs": {},
                }
                return

            # Parse input capture settings
            input_captures = {}
            inputs_config = capture_config.get("inputs", {})
            for param_name, param_config in inputs_config.items():
                if isinstance(param_config, dict):
                    # Convert dict config to Capture object
                    capture = Capture(
                        mode=param_config.get("mode", "metadata"),
                        sample_rate=param_config.get("sample_rate"),
                        max_bytes=param_config.get("max_bytes"),
                        redact=param_config.get("redact"),
                        artifacts=param_config.get("artifacts"),
                    )
                    input_captures[param_name] = capture
                    logger.debug(
                        f"Step '{step_name}' input '{param_name}' has capture setting: {capture}"
                    )

            # Parse output capture settings
            output_captures = {}
            outputs_config = capture_config.get("outputs", {})
            for output_name, output_config in outputs_config.items():
                if isinstance(output_config, dict):
                    # Convert dict config to Capture object
                    capture = Capture(
                        mode=output_config.get("mode", "metadata"),
                        sample_rate=output_config.get("sample_rate"),
                        max_bytes=output_config.get("max_bytes"),
                        redact=output_config.get("redact"),
                        artifacts=output_config.get("artifacts"),
                    )
                    output_captures[output_name] = capture
                    logger.debug(
                        f"Step '{step_name}' output '{output_name}' has capture setting: {capture}"
                    )

            # Store parsed configuration
            input_captures_typed: Dict[str, Optional[Capture]] = input_captures
            output_captures_typed: Dict[
                str, Optional[Capture]
            ] = output_captures
            step_overrides: Dict[str, Dict[str, Optional[Capture]]] = {
                "inputs": input_captures_typed,
                "outputs": output_captures_typed,
            }
            self._step_capture_overrides[step_name] = step_overrides

        except Exception as e:
            logger.warning(
                f"Failed to parse capture configuration for step '{step_name}': {e}"
            )
            # Continue without configuration - this is not a critical failure
            self._step_capture_overrides[step_name] = {
                "inputs": {},
                "outputs": {},
            }

    def _build_execution_order(self) -> None:
        """Build the execution order based on step dependencies.

        This creates a topological sort of the steps based on their
        input/output relationships using ZenML's existing topsort implementation.
        """
        # Build a DAG (Directed Acyclic Graph) from step dependencies
        dag: Dict[str, List[str]] = {}

        for (
            step_name,
            step_config,
        ) in self.deployment.step_configurations.items():
            upstream_steps = []

            # Find upstream steps from input specifications
            for _, input_spec in step_config.spec.inputs.items():
                # Check if this input comes from another step
                if hasattr(input_spec, "step_name") and input_spec.step_name:
                    if (
                        input_spec.step_name != "pipeline"
                    ):  # Not a pipeline parameter
                        upstream_steps.append(input_spec.step_name)

            # Also check for explicit upstream steps if available
            if hasattr(step_config.spec, "upstream_steps"):
                upstream_steps.extend(step_config.spec.upstream_steps)

            # Remove duplicates
            dag[step_name] = list(set(upstream_steps))

        logger.debug(f"Step dependency DAG: {dag}")

        # Create reverse DAG for child lookup
        reversed_dag: Dict[str, List[str]] = {step: [] for step in dag}
        for step, parents in dag.items():
            for parent in parents:
                if parent in reversed_dag:
                    reversed_dag[parent].append(step)

        # Use ZenML's topological sort to get execution layers
        layers = topsorted_layers(
            nodes=list(dag.keys()),
            get_node_id_fn=lambda node: node,
            get_parent_nodes=lambda node: dag.get(node, []),
            get_child_nodes=lambda node: reversed_dag.get(node, []),
        )

        # Flatten layers to get execution order
        # Steps in the same layer could run in parallel, but for now we'll run sequentially
        self._execution_order = []
        for layer in layers:
            self._execution_order.extend(layer)

        logger.debug(
            f"Determined execution order with {len(layers)} layers: "
            f"{self._execution_order}"
        )

    def execute(
        self, parameters: Dict[str, Any], job_id: Optional[str] = None
    ) -> Any:
        """Execute the pipeline with direct data passing and thread-safe context.

        This method executes all pipeline steps in order, passing data
        directly between steps without any serialization or storage.
        Uses contextvars for thread-safe step context management.

        Args:
            parameters: Input parameters for the pipeline
            job_id: Optional job ID for context tracking and event correlation

        Returns:
            The output of the final pipeline step

        Raises:
            RuntimeError: If step execution fails
            asyncio.CancelledError: If execution is cancelled
        """
        start_time = time.time()
        pipeline_name = self.deployment.pipeline_configuration.name

        # Create event builder if callback is provided
        event_builder = None
        if self.event_callback and job_id:
            event_builder = EventBuilder(job_id)

            # Send pipeline started event
            try:
                pipeline_started_event = event_builder.pipeline_started(
                    pipeline_name=pipeline_name, parameters=parameters
                )
                self.event_callback(pipeline_started_event)
            except Exception as e:
                logger.warning(f"Failed to send pipeline started event: {e}")

        # Track outputs from each step
        step_outputs: Dict[str, Any] = {}

        # Add pipeline parameters to step outputs for downstream access
        step_outputs["pipeline"] = parameters

        # Also add parameters directly to step_outputs for easy access
        step_outputs.update(parameters)

        steps_executed = 0
        current_step_index = 0
        total_steps = len(self._execution_order)

        try:
            # Use job context for cross-step tracking
            job_context_manager = (
                serving_job_context(job_id, parameters) if job_id else None
            )

            if job_context_manager:
                with job_context_manager:
                    return self._execute_steps(
                        step_outputs,
                        parameters,
                        event_builder,
                        steps_executed,
                        current_step_index,
                        total_steps,
                        start_time,
                        pipeline_name,
                    )
            else:
                return self._execute_steps(
                    step_outputs,
                    parameters,
                    event_builder,
                    steps_executed,
                    current_step_index,
                    total_steps,
                    start_time,
                    pipeline_name,
                )

        except Exception as e:
            # Send pipeline failed event
            if event_builder and self.event_callback:
                try:
                    failed_event = event_builder.pipeline_failed(
                        pipeline_name=pipeline_name,
                        error=str(e),
                        execution_time=time.time() - start_time,
                        failed_step=self._execution_order[current_step_index]
                        if current_step_index < len(self._execution_order)
                        else None,
                    )
                    self.event_callback(failed_event)
                except Exception as event_error:
                    logger.warning(
                        f"Failed to send pipeline failed event: {event_error}"
                    )
            raise

    def _execute_steps(
        self,
        step_outputs: Dict[str, Any],
        parameters: Dict[str, Any],
        event_builder: Optional[EventBuilder],
        steps_executed: int,
        current_step_index: int,
        total_steps: int,
        start_time: float,
        pipeline_name: str,
    ) -> Any:
        """Execute all steps with proper context management."""
        # Execute each step in order
        for current_step_index, step_name in enumerate(self._execution_order):
            # Check for cancellation before each step
            if self.cancellation_token and self.cancellation_token.is_set():
                raise asyncio.CancelledError(
                    f"Pipeline execution cancelled before step '{step_name}'"
                )

            step_start_time = time.time()

            # Send step started event
            if event_builder and self.event_callback:
                try:
                    step_started_event = event_builder.step_started(step_name)
                    self.event_callback(step_started_event)
                except Exception as e:
                    logger.warning(f"Failed to send step started event: {e}")

            # Send progress update
            if event_builder and self.event_callback:
                try:
                    progress_event = event_builder.progress_update(
                        current_step=current_step_index + 1,
                        total_steps=total_steps,
                        current_step_name=step_name,
                    )
                    self.event_callback(progress_event)
                except Exception as e:
                    logger.warning(f"Failed to send progress event: {e}")

            try:
                # Get step configuration and class
                step_config = self.deployment.step_configurations[step_name]
                step_class = self._loaded_steps[step_name]

                # Resolve inputs for this step
                step_inputs = self._resolve_step_inputs(
                    step_name, step_config, step_outputs, parameters
                )

                logger.debug(
                    f"Executing step '{step_name}' with inputs: "
                    f"{list(step_inputs.keys())}"
                )

                # Execute the step with thread-safe context
                output = self._execute_step(step_name, step_class, step_inputs)

                # Store output for downstream steps
                step_outputs[step_name] = output

                step_duration = time.time() - step_start_time
                steps_executed += 1

                # Call result callback with raw output before serialization
                if self.result_callback:
                    try:
                        self.result_callback(step_name, output, True)
                    except Exception as e:
                        logger.warning(
                            f"Failed to call result callback for step {step_name}: {e}"
                        )

                logger.info(
                    f"Step '{step_name}' completed in {step_duration:.3f}s"
                )

                # Send step completed event
                if event_builder and self.event_callback:
                    try:
                        step_completed_event = event_builder.step_completed(
                            step_name=step_name,
                            execution_time=step_duration,
                            output=output
                            if isinstance(
                                output, (str, int, float, bool, list, dict)
                            )
                            else str(type(output)),
                        )
                        self.event_callback(step_completed_event)
                    except Exception as e:
                        logger.warning(
                            f"Failed to send step completed event: {e}"
                        )

            except Exception as e:
                step_duration = time.time() - step_start_time

                # Call result callback for failed step
                if self.result_callback:
                    try:
                        self.result_callback(step_name, None, False)
                    except Exception as callback_error:
                        logger.warning(
                            f"Failed to call result callback for failed step {step_name}: {callback_error}"
                        )

                # Send step failed event
                if event_builder and self.event_callback:
                    try:
                        step_failed_event = event_builder.step_failed(
                            step_name=step_name,
                            error=str(e),
                            execution_time=step_duration,
                        )
                        self.event_callback(step_failed_event)
                    except Exception as event_error:
                        logger.warning(
                            f"Failed to send step failed event: {event_error}"
                        )

                logger.error(f"Step '{step_name}' failed: {str(e)}")
                raise RuntimeError(
                    f"Pipeline execution failed at step '{step_name}': {str(e)}"
                ) from e

        # Get the output from the last step
        final_output = step_outputs.get(self._execution_order[-1])

        total_duration = time.time() - start_time
        logger.info(f"Pipeline execution completed in {total_duration:.3f}s")

        # Send pipeline completed event
        if event_builder and self.event_callback:
            try:
                completed_event = event_builder.pipeline_completed(
                    pipeline_name=pipeline_name,
                    execution_time=total_duration,
                    result=final_output
                    if isinstance(
                        final_output, (str, int, float, bool, list, dict)
                    )
                    else str(type(final_output)),
                    steps_executed=steps_executed,
                )
                self.event_callback(completed_event)
            except Exception as e:
                logger.warning(f"Failed to send pipeline completed event: {e}")

        return final_output

    def _resolve_step_inputs(
        self,
        step_name: str,
        step_config: "Step",
        step_outputs: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve inputs for a step from previous outputs and parameters.

        This method follows ZenML's standard input resolution process:
        1. Use step.spec.inputs to resolve artifacts from previous steps
        2. Use step.config.parameters for pipeline/step parameters
        3. Match function arguments to resolved inputs/parameters

        Args:
            step_name: Name of the step to resolve inputs for
            step_config: Step configuration
            step_outputs: Outputs from previously executed steps
            parameters: Pipeline input parameters

        Returns:
            Dictionary of resolved inputs for the step
        """
        # Step 1: Resolve input artifacts from step.spec.inputs (previous step outputs)
        input_artifacts = {}
        for input_name, input_spec in step_config.spec.inputs.items():
            source_step_name = input_spec.step_name
            output_name = input_spec.output_name

            logger.debug(
                f"Resolving input '{input_name}' from step '{source_step_name}' output '{output_name}'"
            )

            if source_step_name in step_outputs:
                step_output = step_outputs[source_step_name]

                # Handle multiple outputs by checking if we need a specific output
                resolved_value = self._resolve_step_output(
                    step_output=step_output,
                    output_name=output_name,
                    source_step_name=source_step_name,
                )

                input_artifacts[input_name] = resolved_value
                logger.debug(
                    f"✅ Resolved '{input_name}' from step '{source_step_name}' output '{output_name}' (type: {type(resolved_value).__name__})"
                )
            else:
                logger.warning(
                    f"❌ Source step '{source_step_name}' not found for input '{input_name}'"
                )

        # Step 2: Get step function arguments using proper inspection
        step_class = self._loaded_steps.get(step_name)
        if not step_class or not hasattr(step_class, "entrypoint"):
            logger.error(
                f"Step class or entrypoint not found for '{step_name}'"
            )
            return {}

        try:
            # Use getfullargspec like ZenML's StepRunner does
            spec = inspect.getfullargspec(
                inspect.unwrap(step_class.entrypoint)
            )
            function_args = spec.args

            # Remove 'self' if present
            if function_args and function_args[0] == "self":
                function_args = function_args[1:]

            logger.debug(f"Step function arguments: {function_args}")

        except Exception as e:
            logger.error(
                f"Failed to get function arguments for step '{step_name}': {e}"
            )
            return {}

        # Step 3: Match function arguments to inputs/parameters (like StepRunner._parse_inputs)
        function_params = {}

        # Get all available parameters (runtime parameters have highest priority)
        all_parameters = {}

        # Priority 1: Step config parameters (lowest priority - defaults from deployment)
        if step_config.config.parameters:
            all_parameters.update(step_config.config.parameters)

        # Priority 2: Runtime parameters (highest priority - from API request)
        all_parameters.update(parameters)

        for arg_name in function_args:
            logger.debug(f"Resolving function argument '{arg_name}'")

            # Priority 1: Input artifacts (from previous steps)
            if arg_name in input_artifacts:
                function_params[arg_name] = input_artifacts[arg_name]

            # Priority 2: Parameters (pipeline or step parameters)
            elif arg_name in all_parameters:
                function_params[arg_name] = all_parameters[arg_name]

            else:
                logger.error(
                    f"❌ Unable to resolve function argument '{arg_name}' for step '{step_name}'"
                )
                logger.error(
                    f"Available input artifacts: {list(input_artifacts.keys())}"
                )
                logger.error(
                    f"Available parameters: {list(all_parameters.keys())}"
                )
                # This should cause the step to fail, matching ZenML's behavior
                raise RuntimeError(
                    f"Unable to find value for step function argument `{arg_name}`."
                )

        return function_params

    def _resolve_step_output(
        self, step_output: Any, output_name: str, source_step_name: str
    ) -> Any:
        """Resolve a specific output from a step's return value.

        This handles the common cases for ZenML step outputs:
        1. Single output: return the output directly
        2. Multiple outputs as dict: {"output1": val1, "output2": val2}
        3. Multiple outputs as tuple/list: (val1, val2) with positional matching

        Args:
            step_output: The raw output from the step function
            output_name: The name of the specific output we want
            source_step_name: Name of the source step (for error messages)

        Returns:
            The resolved output value
        """
        # Case 1: If output_name is "output" or empty, assume single output
        if not output_name or output_name == "output":
            logger.debug(
                f"Using entire output from step '{source_step_name}' (single output)"
            )
            return step_output

        # Case 2: Multiple outputs as dictionary
        if isinstance(step_output, dict):
            if output_name in step_output:
                logger.debug(
                    f"Found named output '{output_name}' in dict from step '{source_step_name}'"
                )
                return step_output[output_name]
            else:
                # If the requested output name is not in the dict, but there's only one item,
                # assume it's a single output case and return the whole thing
                if len(step_output) == 1:
                    logger.debug(
                        f"Single dict output from step '{source_step_name}', returning entire output"
                    )
                    return step_output
                else:
                    available = list(step_output.keys())
                    logger.warning(
                        f"Output '{output_name}' not found in step '{source_step_name}' dict outputs. "
                        f"Available: {available}. Using entire output."
                    )
                    return step_output

        # Case 3: Multiple outputs as tuple/list - we can't resolve by name without spec
        # So we'll return the entire output and let the receiving step handle it
        elif isinstance(step_output, (tuple, list)):
            logger.debug(
                f"Step '{source_step_name}' returned tuple/list with {len(step_output)} items. "
                f"Cannot resolve '{output_name}' without output specification. Using entire output."
            )
            return step_output

        # Case 4: Single value output
        else:
            logger.debug(
                f"Single value output from step '{source_step_name}', returning entire output"
            )
            return step_output

    def _execute_step(
        self, step_name: str, step_class: type, inputs: Dict[str, Any]
    ) -> Any:
        """Execute a single step with given inputs using thread-safe context.

        This method handles the actual step execution using contextvars for
        thread-safe step context management. No more dangerous monkey patching!

        Args:
            step_name: Name of the step being executed
            step_class: The step class to instantiate and execute
            inputs: Input data for the step

        Returns:
            The output of the step execution
        """
        # Use thread-safe serving step context
        with serving_step_context(step_name):
            try:
                # Get the entrypoint function directly from the step class and call it
                logger.debug(
                    f"Executing step '{step_name}' with inputs: {inputs}"
                )
                entrypoint_func = getattr(step_class, "entrypoint", None)
                if not entrypoint_func:
                    raise RuntimeError(
                        f"Step class {step_class} has no entrypoint method"
                    )
                result = entrypoint_func(**inputs)

                return result

            except Exception as e:
                logger.error(f"Error executing step '{step_name}': {str(e)}")
                raise

    def get_step_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about loaded steps.

        Returns:
            Dictionary with step names as keys and step info as values
        """
        step_info = {}

        for step_name, step_class in self._loaded_steps.items():
            step_config = self.deployment.step_configurations[step_name]

            step_info[step_name] = {
                "name": step_name,
                "source": step_config.spec.source,
                "inputs": list(step_config.spec.inputs.keys()),
                "loaded": step_class is not None,
            }

        return step_info

    def get_step_capture_overrides(
        self,
    ) -> Dict[str, Dict[str, Dict[str, Optional[Capture]]]]:
        """Get parsed capture annotations for all steps.

        Returns:
            Dictionary mapping step names to their input/output capture annotations
        """
        return self._step_capture_overrides.copy()
