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
"""Core pipeline serving service implementation.

This service defers all execution responsibilities to the orchestrator
configured in the deployment stack. It only resolves request parameters,
applies them to the loaded deployment, and triggers the orchestrator.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.topsort import topsorted_layers
from zenml.stack import Stack

logger = get_logger(__name__)


class PipelineServingService:
    """Core service for serving ZenML pipelines via FastAPI.

    This service handles the loading, execution, and monitoring of ZenML pipelines
    in a serving context. It provides both synchronous and streaming execution
    capabilities while maintaining compatibility with ZenML's existing execution
    infrastructure.
    """

    def __init__(self, deployment_id: str):
        """Initialize the pipeline serving service.

        Args:
            deployment_id: UUID of the pipeline deployment to serve
        """
        self.deployment_id = deployment_id
        self.deployment: Optional[PipelineDeploymentResponse] = None
        self.parameter_schema: Dict[str, Any] = {}
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None

        # Execution statistics
        self.execution_stats: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "executions_24h": [],  # Store timestamps for 24h tracking
        }

        logger.info(
            f"Initializing PipelineServingService for deployment: {deployment_id}"
        )

    async def initialize(self) -> None:
        """Initialize the service by loading deployment configuration.

        This method loads the pipeline deployment, extracts parameter schema,
        and sets up the execution environment.

        Raises:
            ValueError: If deployment ID is invalid or deployment not found
            Exception: If initialization fails
        """
        try:
            logger.info("Loading pipeline deployment configuration...")

            # Load deployment from ZenML store
            client = Client()

            # Convert deployment_id to UUID safely
            try:
                if isinstance(self.deployment_id, str):
                    deployment_uuid = UUID(self.deployment_id)
                else:
                    deployment_uuid = self.deployment_id
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid deployment ID format: {self.deployment_id}"
                ) from e

            self.deployment = client.zen_store.get_deployment(
                deployment_id=deployment_uuid
            )

            # Activate integrations to ensure all components are available
            integration_registry.activate_integrations()

            # Extract parameter schema for validation
            self.parameter_schema = self._extract_parameter_schema()

            # Default serving to no-capture unless explicitly set
            try:
                current_settings = (
                    self.deployment.pipeline_configuration.settings or {}
                )
                if "capture" not in current_settings:
                    # Create new pipeline configuration with updated settings
                    new_settings = {**current_settings, "capture": "none"}
                    self.deployment.pipeline_configuration = (
                        self.deployment.pipeline_configuration.model_copy(
                            update={"settings": new_settings}
                        )
                    )
            except Exception:
                # Best-effort only; if settings are immutable or unavailable, continue
                pass

            # Log successful initialization
            pipeline_name = self.deployment.pipeline_configuration.name
            step_count = len(self.deployment.step_configurations)

            logger.info("✅ Service initialized successfully:")
            logger.info(f"   Pipeline: {pipeline_name}")
            logger.info(f"   Steps: {step_count}")
            logger.info(
                f"   Stack: {self.deployment.stack.name if self.deployment.stack else 'unknown'}"
            )
            logger.info(f"   Parameters: {list(self.parameter_schema.keys())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {str(e)}")
            logger.error(f"   Error type: {type(e)}")
            import traceback

            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    def _extract_parameter_schema(self) -> Dict[str, Any]:
        """Extract parameter schema from pipeline deployment and function signature.

        Returns:
            Dictionary containing parameter information with types and defaults
        """
        schema: Dict[str, Any] = {}

        if not self.deployment:
            return schema

        deployment = self.deployment  # Local var for type narrowing

        # Get parameters from pipeline configuration
        pipeline_params = deployment.pipeline_configuration.parameters or {}

        for param_name, param_value in pipeline_params.items():
            # Handle parameter type safely
            try:
                param_type = (
                    type(param_value).__name__
                    if param_value is not None
                    else "NoneType"
                )
            except Exception:
                param_type = "unknown"

            schema[param_name] = {
                "type": param_type,
                "default": param_value,
                "required": False,  # Since it has a default
            }

        # Enhanced: Extract parameters from pipeline function signature
        try:
            # Get the pipeline source and load it to inspect the function signature
            pipeline_spec = getattr(
                self.deployment.pipeline_configuration, "spec", None
            )
            if pipeline_spec and getattr(pipeline_spec, "source", None):
                import inspect

                from zenml.utils import source_utils

                # Load the pipeline function
                pipeline_func = source_utils.load(pipeline_spec.source)

                # Get function signature
                sig = inspect.signature(pipeline_func)

                for param_name, param in sig.parameters.items():
                    # Skip if we already have this parameter from deployment config
                    if param_name in schema:
                        continue

                    # Extract type information
                    param_type = "str"  # Default fallback
                    if param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, "__name__"):
                            param_type = param.annotation.__name__
                        else:
                            param_type = str(param.annotation)

                    # Extract default value
                    has_default = param.default != inspect.Parameter.empty
                    default_value = param.default if has_default else None

                    schema[param_name] = {
                        "type": param_type,
                        "default": default_value,
                        "required": not has_default,
                    }

                    logger.debug(
                        f"Extracted function parameter: {param_name} ({param_type}) = {default_value}"
                    )

        except Exception as e:
            logger.warning(
                f"Failed to extract pipeline function signature: {e}"
            )
            # Continue with just deployment parameters

        logger.debug(f"Final extracted parameter schema: {schema}")
        return schema

    def _resolve_parameters(
        self, request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve pipeline parameters with request overrides.

        Args:
            request_params: Parameters provided in the API request

        Returns:
            Dictionary of resolved parameters (deployment defaults overridden)
        """
        defaults: Dict[str, Any] = {}
        if self.deployment:
            defaults = self.deployment.pipeline_configuration.parameters or {}
        resolved = {**defaults, **(request_params or {})}
        logger.debug(f"Resolved parameters: {list(resolved.keys())}")
        return resolved

    def _apply_parameter_overrides(self, params: Dict[str, Any]) -> None:
        """Apply parameter overrides to the loaded deployment in-place.

        - Update `deployment.pipeline_configuration.parameters`
        - For each step, override matching keys in `step.config.parameters`
        """
        if not self.deployment:
            return

        # Update pipeline-level parameters using model_copy
        pipeline_conf = self.deployment.pipeline_configuration
        new_parameters = {
            **(pipeline_conf.parameters or {}),
            **params,
        }
        self.deployment.pipeline_configuration = pipeline_conf.model_copy(
            update={"parameters": new_parameters}
        )

        # Propagate overrides into step parameters when keys match
        for step_cfg in self.deployment.step_configurations.values():
            step_params = step_cfg.config.parameters or {}
            updated = False
            for k, v in params.items():
                if k in step_params:
                    step_params[k] = v
                    updated = True
            if updated:
                # Create new step config with updated parameters
                step_cfg.config = step_cfg.config.model_copy(
                    update={"parameters": step_params}
                )

    def _build_pipeline_response(
        self, tracking_disabled: bool
    ) -> Dict[str, Any]:
        """Build the pipeline response with actual outputs.

        Args:
            tracking_disabled: Whether tracking is disabled

        Returns:
            Dictionary containing the pipeline outputs
        """
        if not self.deployment:
            return {}

        # Extract return contract from pipeline function
        pipeline_spec = getattr(
            self.deployment.pipeline_configuration, "spec", None
        )
        pipeline_source = (
            getattr(pipeline_spec, "source", None) if pipeline_spec else None
        )

        return_contract = orchestrator_utils.extract_return_contract(
            pipeline_source
        )

        if tracking_disabled:
            # Use tap outputs directly (in-memory)
            outputs = {}
            if return_contract:
                for output_name, step_name in return_contract.items():
                    step_outputs = orchestrator_utils.tap_get_step_outputs(
                        step_name
                    )
                    if step_outputs:
                        # For simplicity, take the first output of the step
                        first_output = next(iter(step_outputs.values()), None)
                        if first_output is not None:
                            outputs[output_name] = self._serialize_for_json(
                                first_output
                            )
            else:
                # Fallback: return all step outputs
                all_tap_outputs = orchestrator_utils._serve_output_tap.get({})
                for step_name, step_outputs in all_tap_outputs.items():
                    for output_name, output_value in step_outputs.items():
                        outputs[f"{step_name}_{output_name}"] = (
                            self._serialize_for_json(output_value)
                        )

            return outputs
        else:
            # TODO: For full tracking mode, materialize artifacts and return
            return {
                "message": "Full tracking mode outputs not yet implemented"
            }

    def _serialize_for_json(self, value: Any) -> Any:
        """Serialize a value for JSON response with proper numpy/pandas handling.

        Args:
            value: The value to serialize

        Returns:
            JSON-serializable representation of the value
        """
        try:
            import json

            # Handle common ML types that aren't JSON serializable
            if hasattr(value, "tolist"):  # numpy arrays, pandas Series
                return value.tolist()
            elif hasattr(value, "to_dict"):  # pandas DataFrames
                return value.to_dict()
            elif hasattr(value, "__array__"):  # numpy-like arrays
                import numpy as np

                return np.asarray(value).tolist()

            # Test if it's already JSON serializable
            json.dumps(value)
            return value
        except (TypeError, ValueError, ImportError):
            # Safe fallback with size limit for large objects
            str_repr = str(value)
            if len(str_repr) > 1000:  # Truncate very large objects
                return f"{str_repr[:1000]}... [truncated, original length: {len(str_repr)}]"
            return str_repr

    async def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """Execute pipeline synchronously by invoking BaseOrchestrator.run_step."""
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        start = time.time()
        logger.info("Starting pipeline execution")
        try:
            resolved_params = self._resolve_parameters(parameters)
            self._apply_parameter_overrides(resolved_params)

            # Clear tap for fresh request
            orchestrator_utils.tap_clear()

            # Build execution order using the production-tested topsort utility
            deployment = self.deployment
            steps = deployment.step_configurations
            node_ids = list(steps.keys())
            parent_map: Dict[str, List[str]] = {
                name: [
                    p for p in steps[name].spec.upstream_steps if p in steps
                ]
                for name in node_ids
            }
            child_map: Dict[str, List[str]] = {name: [] for name in node_ids}
            for child, parents in parent_map.items():
                for p in parents:
                    child_map[p].append(child)

            layers = topsorted_layers(
                nodes=node_ids,
                get_node_id_fn=lambda n: n,
                get_parent_nodes=lambda n: parent_map[n],
                get_child_nodes=lambda n: child_map[n],
            )
            order: List[str] = [n for layer in layers for n in layer]

            # In no-capture mode, disable step retries and step operators
            if orchestrator_utils.is_tracking_disabled(
                deployment.pipeline_configuration.settings
            ):
                for step_cfg in steps.values():
                    try:
                        if step_cfg.config.retry is not None:
                            # Create new retry config with disabled settings
                            new_retry = step_cfg.config.retry.model_copy(
                                update={
                                    "max_retries": 0,
                                    "delay": 0,
                                    "backoff": 1,
                                }
                            )
                            step_cfg.config = step_cfg.config.model_copy(
                                update={"retry": new_retry}
                            )
                    except Exception:
                        pass
                    try:
                        # Create new config without step operator
                        step_cfg.config = step_cfg.config.model_copy(
                            update={"step_operator": None}
                        )
                    except Exception:
                        pass

            # Use orchestrator.run_step only (no full orchestrator.run)
            assert deployment.stack is not None
            stack = Stack.from_model(deployment.stack)
            orchestrator = stack.orchestrator
            # Ensure a stable run id for StepLauncher to reuse the same PipelineRun
            if hasattr(orchestrator, "_orchestrator_run_id"):
                setattr(orchestrator, "_orchestrator_run_id", str(uuid4()))

            # Prepare, run each step, inject inputs in no-capture, collect outputs, then cleanup
            orchestrator._prepare_run(deployment=deployment)
            try:
                tracking_disabled = orchestrator_utils.is_tracking_disabled(
                    deployment.pipeline_configuration.settings
                )
                for step_name in order:
                    step_cfg = steps[step_name]

                    # Inject upstream outputs as step parameters for in-memory handoff
                    if tracking_disabled:
                        for (
                            arg_name,
                            input_spec,
                        ) in step_cfg.spec.inputs.items():
                            if (
                                input_spec.step_name != "pipeline"
                            ):  # Skip pipeline-level params
                                upstream_outputs = (
                                    orchestrator_utils.tap_get_step_outputs(
                                        input_spec.step_name
                                    )
                                )
                                if (
                                    upstream_outputs
                                    and input_spec.output_name
                                    in upstream_outputs
                                ):
                                    # Create new step config with injected parameters
                                    current_params = (
                                        step_cfg.config.parameters or {}
                                    )
                                    new_params = {
                                        **current_params,
                                        arg_name: upstream_outputs[
                                            input_spec.output_name
                                        ],
                                    }
                                    step_cfg.config = (
                                        step_cfg.config.model_copy(
                                            update={"parameters": new_params}
                                        )
                                    )

                    orchestrator.run_step(step_cfg)
            finally:
                orchestrator._cleanup_run()
                # Clear tap to avoid memory leaks between requests
                if tracking_disabled:
                    orchestrator_utils.tap_clear()

            # Build response with actual pipeline outputs
            outputs = self._build_pipeline_response(tracking_disabled)

            execution_time = time.time() - start
            self._update_execution_stats(True, execution_time)
            self.last_execution_time = datetime.now(timezone.utc)
            return {
                "success": True,
                "outputs": outputs,
                "execution_time": execution_time,
                "metadata": {
                    "pipeline_name": self.deployment.pipeline_configuration.name,
                    "parameters_used": resolved_params,
                    "deployment_id": str(self.deployment.id),
                    "steps_executed": len(order),
                },
            }
        except asyncio.TimeoutError:
            execution_time = time.time() - start
            self._update_execution_stats(False, execution_time)
            return {
                "success": False,
                "job_id": None,
                "error": f"Pipeline execution timed out after {timeout}s",
                "execution_time": execution_time,
                "metadata": {},
            }
        except Exception as e:  # noqa: BLE001
            execution_time = time.time() - start
            self._update_execution_stats(False, execution_time)
            logger.error(f"❌ Pipeline execution failed: {e}")
            return {
                "success": False,
                "job_id": None,
                "error": str(e),
                "execution_time": execution_time,
                "metadata": {},
            }

    async def submit_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 600,
    ) -> Dict[str, Any]:
        """Submit pipeline for asynchronous execution using the orchestrator."""
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        resolved_params = self._resolve_parameters(parameters)

        async def _background() -> None:
            try:
                await self.execute_pipeline(
                    parameters=resolved_params,
                    run_name=run_name,
                    timeout=timeout,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"Background execution failed: {e}")

        asyncio.create_task(_background())
        return {
            "success": True,
            "job_id": None,
            "message": "Pipeline execution submitted successfully",
            "status": "submitted",
            "metadata": {
                "job_id": None,
                "pipeline_name": self.deployment.pipeline_configuration.name,
                "parameters_used": resolved_params,
                "deployment_id": self.deployment_id,
            },
        }

    # No direct execution engine here; we rely on the orchestrator

    class _SimpleEvent(BaseModel):
        event: str = Field(description="Event type")
        message: Optional[str] = None
        timestamp: str = Field(
            default_factory=lambda: datetime.now(timezone.utc).isoformat()
        )

    async def execute_pipeline_streaming(
        self, parameters: Dict[str, Any], run_name: Optional[str] = None
    ) -> AsyncGenerator[_SimpleEvent, None]:
        """Execute pipeline with minimal streaming updates."""
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        yield self._SimpleEvent(
            event="pipeline_started", message="Execution started"
        )
        try:
            result = await self.execute_pipeline(
                parameters=parameters, run_name=run_name
            )
            if result.get("success"):
                yield self._SimpleEvent(
                    event="pipeline_completed", message="Execution completed"
                )
            else:
                yield self._SimpleEvent(
                    event="pipeline_failed", message=result.get("error")
                )
        except Exception as e:  # noqa: BLE001
            yield self._SimpleEvent(event="pipeline_failed", message=str(e))

    def _update_execution_stats(
        self, success: bool, execution_time: float
    ) -> None:
        """Update execution statistics.

        Args:
            success: Whether the execution was successful
            execution_time: Execution time in seconds
        """
        current_time = datetime.now(timezone.utc)

        # Update counters
        self.execution_stats["total_executions"] += 1
        if success:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1

        # Update timing
        self.execution_stats["total_execution_time"] += execution_time

        # Track 24h executions
        self.execution_stats["executions_24h"].append(current_time)

        # Clean up old 24h entries (keep only last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.execution_stats["executions_24h"] = [
            ts
            for ts in self.execution_stats["executions_24h"]
            if ts > cutoff_time
        ]

    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics and statistics.

        Returns:
            Dictionary containing execution metrics
        """
        stats = self.execution_stats
        total_executions = max(
            stats["total_executions"], 1
        )  # Avoid division by zero

        return {
            "total_executions": stats["total_executions"],
            "successful_executions": stats["successful_executions"],
            "failed_executions": stats["failed_executions"],
            "success_rate": stats["successful_executions"] / total_executions,
            "average_execution_time": stats["total_execution_time"]
            / total_executions,
            "last_24h_executions": len(stats["executions_24h"]),
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information including pipeline and deployment details.

        Returns:
            Dictionary containing service information
        """
        if not self.deployment:
            return {"error": "Service not initialized"}

        return {
            "service": {
                "name": "ZenML Pipeline Serving",
                "version": "0.1.0",
                "deployment_id": self.deployment_id,
                "uptime": time.time() - self.service_start_time,
                "status": "healthy",
            },
            "pipeline": {
                "name": self.deployment.pipeline_configuration.name,
                "steps": list(self.deployment.step_configurations.keys()),
                "parameters": self.parameter_schema,
            },
            "deployment": {
                "id": self.deployment_id,
                "created_at": self.deployment.created,
                "stack": self.deployment.stack.name
                if self.deployment.stack
                else "unknown",
            },
        }

    def is_healthy(self) -> bool:
        """Check if the service is healthy and ready to serve requests.

        Returns:
            True if service is healthy, False otherwise
        """
        return self.deployment is not None
