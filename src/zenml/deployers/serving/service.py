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
import inspect
import json
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.orchestrators.topsort import topsorted_layers
from zenml.orchestrators.utils import (
    extract_return_contract,
    is_tracking_disabled,
    response_tap_clear,
    response_tap_get_all,
    set_pipeline_state,
    set_return_targets,
    set_serving_context,
)
from zenml.stack import Stack
from zenml.utils import source_utils

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
        self.pipeline_state: Optional[Any] = None

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

            # Execute the init hook, if present
            self._execute_init_hook()

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
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    async def cleanup(self) -> None:
        """Cleanup the service by executing the pipeline's cleanup hook, if present."""
        if not self.deployment:
            return

        if self.deployment.pipeline_configuration.cleanup_hook_source:
            logger.info("Executing pipeline's cleanup hook...")
            try:
                cleanup_hook = source_utils.load(
                    self.deployment.pipeline_configuration.cleanup_hook_source
                )
            except Exception as e:
                logger.exception(f"Failed to load the cleanup hook: {e}")
                raise
            try:
                cleanup_hook()
            except Exception as e:
                logger.exception(f"Failed to execute cleanup hook: {e}")
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

    def _execute_init_hook(self) -> None:
        """Execute the pipeline's init hook, if present."""
        if not self.deployment:
            return

        if self.deployment.pipeline_configuration.init_hook_source:
            logger.info("Executing pipeline's init hook...")
            try:
                init_hook = source_utils.load(
                    self.deployment.pipeline_configuration.init_hook_source
                )
            except Exception as e:
                logger.exception(f"Failed to load the init hook: {e}")
                raise
            try:
                self.pipeline_state = init_hook()
            except Exception as e:
                logger.exception(f"Failed to execute init hook: {e}")
                raise

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

    def _serialize_for_json(self, value: Any) -> Any:
        """Serialize a value for JSON response with proper numpy/pandas handling.

        Args:
            value: The value to serialize

        Returns:
            JSON-serializable representation of the value
        """
        try:
            # Handle common ML types that aren't JSON serializable
            if hasattr(value, "tolist"):  # numpy arrays, pandas Series
                return value.tolist()
            elif hasattr(value, "to_dict"):  # pandas DataFrames
                return value.to_dict()
            elif hasattr(value, "__array__"):  # numpy-like arrays
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

        # Set up response capture
        response_tap_clear()
        self._setup_return_targets()

        try:
            # Resolve request parameters
            resolved_params = self._resolve_parameters(parameters)
            # Expose resolved params to launcher/runner via env for memory-only path
            os.environ["ZENML_SERVING_REQUEST_PARAMS"] = json.dumps(
                resolved_params
            )
            # Expose pipeline state via serving context var
            set_pipeline_state(self.pipeline_state)

            # Get deployment and check if we're in no-capture mode
            deployment = self.deployment
            _ = is_tracking_disabled(
                deployment.pipeline_configuration.settings
            )

            # Mark serving context for the orchestrator/launcher
            set_serving_context(True)

            # Build execution order using the production-tested topsort utility
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

            # No-capture optimizations handled by effective config in StepLauncher

            # Use orchestrator.run_step only (no full orchestrator.run)
            assert deployment.stack is not None
            stack = Stack.from_model(deployment.stack)

            # Note: No artifact store override needed with tap mechanism

            orchestrator = stack.orchestrator
            # Ensure a stable run id for StepLauncher to reuse the same PipelineRun
            run_uuid = str(uuid4())
            if hasattr(orchestrator, "_orchestrator_run_id"):
                setattr(orchestrator, "_orchestrator_run_id", run_uuid)

            # No serving overrides population in local orchestrator path

            # Prepare, run each step (standard local orchestrator behavior), then cleanup
            orchestrator._prepare_run(deployment=deployment)
            try:
                for step_name in order:
                    orchestrator.run_step(steps[step_name])

            finally:
                orchestrator._cleanup_run()
                # Clear serving context marker
                set_serving_context(False)
                # Clear request params env and shared runtime state
                os.environ.pop("ZENML_SERVING_REQUEST_PARAMS", None)
                set_pipeline_state(None)
                # No per-request capture override to clear
                try:
                    from zenml.orchestrators.runtime_manager import (
                        clear_shared_runtime,
                        reset_memory_runtime_for_run,
                    )

                    reset_memory_runtime_for_run(run_uuid)
                    clear_shared_runtime()
                except Exception:
                    pass

            # Get captured outputs from response tap
            outputs = response_tap_get_all()

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
        finally:
            # Clean up response tap
            response_tap_clear()

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

    def _setup_return_targets(self) -> None:
        """Set up return targets for response capture based on pipeline contract."""
        try:
            deployment = self.deployment
            if not deployment:
                return

            # Extract return contract with safe attribute access
            pipeline_spec = getattr(
                deployment.pipeline_configuration, "spec", None
            )
            pipeline_source = (
                getattr(pipeline_spec, "source", None)
                if pipeline_spec
                else None
            )
            contract = (
                extract_return_contract(pipeline_source)
                if pipeline_source
                else None
            )

            logger.debug(f"Pipeline source: {pipeline_source}")
            logger.debug(f"Return contract: {contract}")

            return_targets: Dict[str, Optional[str]] = {}

            if contract:
                # Use return contract: step_name -> expected_output_name
                return_targets = {
                    step_name: output_name
                    for output_name, step_name in contract.items()
                }
            else:
                # Fallback: collect first output of terminal steps
                step_configs = deployment.step_configurations
                terminal_steps = []

                # Find terminal steps (no downstream dependencies)
                for step_name, _ in step_configs.items():
                    has_downstream = any(
                        step_name in other_config.spec.upstream_steps
                        for other_name, other_config in step_configs.items()
                        if other_name != step_name
                    )
                    if not has_downstream:
                        terminal_steps.append(step_name)

                # Target first output of each terminal step
                return_targets = {
                    step_name: None for step_name in terminal_steps
                }
                logger.debug(
                    f"Using terminal steps fallback: {terminal_steps}"
                )

            logger.debug(f"Return targets: {return_targets}")
            set_return_targets(return_targets)

        except Exception as e:
            logger.warning(f"Failed to setup return targets: {e}")
            # Set empty targets as fallback
            set_return_targets({})

    def is_healthy(self) -> bool:
        """Check if the service is healthy and ready to serve requests.

        Returns:
            True if service is healthy, False otherwise
        """
        return self.deployment is not None
