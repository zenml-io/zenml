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
"""Modified entrypoint configuration for pipeline serving."""

import os
import sys
from typing import TYPE_CHECKING, Any, Dict
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.serving.direct_execution import DirectExecutionEngine

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)


class ServingPipelineEntrypoint(PipelineEntrypointConfiguration):
    """Modified pipeline entrypoint for serving with runtime parameters.

    This class extends the standard PipelineEntrypointConfiguration to support
    runtime parameter injection for pipeline serving use cases using direct
    execution without orchestrators.
    """

    def __init__(self, deployment_id: str, runtime_params: Dict[str, Any], 
                 create_zen_run: bool = False):
        """Initialize the serving entrypoint.

        Args:
            deployment_id: UUID of the pipeline deployment to execute
            runtime_params: Parameters to inject at runtime
            create_zen_run: If True, create and track a ZenML pipeline run.
                This should be True when called from ZenML interfaces and
                False when called from regular HTTP endpoints.
        """
        # Skip parent initialization and argument parsing
        # Set up entrypoint args directly
        self.entrypoint_args = {"deployment_id": deployment_id}
        self.runtime_params = runtime_params
        self.create_zen_run = create_zen_run
        logger.debug(
            f"Serving entrypoint initialized with params: {runtime_params}, "
            f"create_zen_run: {create_zen_run}"
        )

    def load_deployment(self) -> "PipelineDeploymentResponse":
        """Load the deployment configuration.

        Returns:
            The pipeline deployment configuration
        """
        deployment_id = UUID(self.entrypoint_args["deployment_id"])
        return Client().zen_store.get_deployment(deployment_id=deployment_id)

    def run(self) -> Dict[str, Any]:
        """Execute the pipeline with runtime parameters using direct execution.

        Returns:
            Dictionary containing execution results and metadata

        Raises:
            Exception: If pipeline execution fails
        """
        logger.info("Using direct execution mode for pipeline serving")
        return self._run_direct_execution()
    
    def _run_direct_execution(self) -> Dict[str, Any]:
        """Execute pipeline using direct execution engine.
        
        This method uses the DirectExecutionEngine to execute the pipeline
        without orchestrators, artifact stores, or caching. It optionally
        creates a ZenML pipeline run for tracking purposes when called from
        ZenML interfaces.
        
        Returns:
            Dictionary containing execution results and metadata
        """
        logger.info(f"Starting direct pipeline execution (create_zen_run={self.create_zen_run})")
        
        # Load deployment configuration
        deployment = self.load_deployment()
        
        # Inject runtime parameters into deployment
        deployment = self._create_runtime_deployment(deployment)
        
        # Activate all integrations to ensure materializers and flavors are loaded
        integration_registry.activate_integrations()
        
        # Download code if necessary (for remote execution environments)
        self.download_code_if_necessary(deployment=deployment)
        
        # Set up working directory for code execution
        # For containerized environments, use /app
        if os.path.exists("/app"):
            os.chdir("/app")
        
        # Add current directory to Python path if not already present
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
            
        # TODO: Delete this after testing
            
        # Also add the directory where we might expect to find the pipeline modules
        # This is typically the directory where the serving was started from
        serving_dirs = [
            ".",  # Current directory
            "./examples/serving",  # Common examples location
            os.path.join(os.getcwd(), "examples", "serving"),  # Full path to examples
        ]
        
        for serving_dir in serving_dirs:
            if os.path.exists(serving_dir) and serving_dir not in sys.path:
                abs_path = os.path.abspath(serving_dir)
                sys.path.insert(0, abs_path)
                logger.debug(f"Added {abs_path} to Python path")
        
        # Optionally create a pipeline run for tracking
        placeholder_run = None
        if self.create_zen_run:
            try:
                logger.info("Creating ZenML pipeline run for tracking...")
                from zenml.pipelines.run_utils import create_placeholder_run
                
                # Create a placeholder run for tracking
                placeholder_run = create_placeholder_run(deployment=deployment)
                logger.info(f"Created pipeline run: {placeholder_run.id}")
            except Exception as e:
                logger.warning(f"Failed to create pipeline run: {e}. Continuing without tracking.")
                placeholder_run = None
        
        try:
            # Create and initialize direct execution engine
            engine = DirectExecutionEngine(
                deployment=deployment,
                pipeline_run=placeholder_run  # Pass run for context if available
            )
            
            # Execute pipeline directly
            output = engine.execute(self.runtime_params)
            
            # Get execution metadata
            step_info = engine.get_step_info()
            
            # Update pipeline run status if we created one
            if placeholder_run:
                try:
                    from zenml.client import Client
                    from zenml.enums import ExecutionStatus
                    
                    Client().zen_store.update_run(
                        run_id=placeholder_run.id,
                        run_update={"status": ExecutionStatus.COMPLETED}
                    )
                    logger.info(f"Updated pipeline run {placeholder_run.id} to COMPLETED")
                except Exception as e:
                    logger.warning(f"Failed to update pipeline run status: {e}")
            
            logger.info("✅ Direct pipeline execution completed successfully")
            
            return {
                "pipeline_name": deployment.pipeline_configuration.name,
                "deployment_id": str(deployment.id),
                "run_id": str(placeholder_run.id) if placeholder_run else None,
                "steps_executed": len(step_info),
                "runtime_parameters": self.runtime_params,
                "status": "completed",
                "output": output,
                "execution_mode": "direct",
                "step_info": step_info,
                "tracked": bool(placeholder_run),
            }
            
        except Exception as e:
            logger.error(f"❌ Direct pipeline execution failed: {str(e)}")
            
            # Update pipeline run status if we created one
            if placeholder_run:
                try:
                    from zenml.client import Client
                    from zenml.enums import ExecutionStatus
                    
                    Client().zen_store.update_run(
                        run_id=placeholder_run.id,
                        run_update={"status": ExecutionStatus.FAILED}
                    )
                except Exception:
                    pass  # Ignore failures in error handling
            
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _create_runtime_deployment(
        self, deployment: "PipelineDeploymentResponse"
    ) -> "PipelineDeploymentResponse":
        """Create a new deployment with runtime parameters injected.

        Since ZenML deployment models are frozen (immutable), we need to create
        a new deployment with updated parameters rather than modifying in place.

        Args:
            deployment: The original pipeline deployment

        Returns:
            A new deployment with runtime parameters injected
        """
        if not self.runtime_params:
            logger.debug("No runtime parameters to inject")
            return deployment

        # Get current pipeline parameters
        current_params = deployment.pipeline_configuration.parameters or {}

        # Merge runtime parameters with existing parameters
        # Runtime parameters take precedence
        merged_params = {**current_params, **self.runtime_params}

        # Create a new pipeline configuration with merged parameters
        updated_pipeline_config = deployment.pipeline_configuration.model_copy(
            update={"parameters": merged_params}
        )

        # Create a new deployment with the updated pipeline configuration
        updated_deployment = deployment.model_copy(
            update={"pipeline_configuration": updated_pipeline_config}
        )
        
        # Verify the parameters were actually injected
        logger.info(f"Updated deployment pipeline parameters: {updated_deployment.pipeline_configuration.parameters}")

        # Debug updated deployment after copy
        logger.info(f"Updated deployment step count after copy: {len(updated_deployment.step_configurations)}")
        logger.info(f"Updated deployment step names after copy: {list(updated_deployment.step_configurations.keys())}")

        # Also inject parameters into step configurations if needed
        updated_deployment = self._inject_step_parameters(updated_deployment)
        
        # Debug final deployment
        logger.info(f"Final deployment step count: {len(updated_deployment.step_configurations)}")
        logger.info(f"Final deployment step names: {list(updated_deployment.step_configurations.keys())}")

        logger.debug(
            f"Created runtime deployment with parameters: {list(merged_params.keys())}"
        )

        return updated_deployment

    def _inject_step_parameters(
        self, deployment: "PipelineDeploymentResponse"
    ) -> "PipelineDeploymentResponse":
        """Inject step-level runtime parameters based on step function signatures.

        Args:
            deployment: The pipeline deployment to process

        Returns:
            A new deployment with updated step parameters
        """
        updated_step_configs = {}
        
        for step_name, step_config in deployment.step_configurations.items():
            # Get step function signature to determine valid parameters
            step_spec = step_config.spec
            step_signature = self._get_step_signature(step_spec)

            # Find runtime parameters that match this step's signature
            step_runtime_params = {
                param_name: param_value
                for param_name, param_value in self.runtime_params.items()
                if param_name in step_signature
            }

            if step_runtime_params:
                # Get existing step parameters
                current_step_params = step_config.config.parameters or {}

                # Log parameter conflicts for debugging
                conflicts = self._detect_parameter_conflicts(
                    current_step_params, step_runtime_params
                )
                if conflicts:
                    logger.warning(
                        f"Step '{step_name}' parameter conflicts (runtime overrides config): {conflicts}"
                    )

                # Merge parameters with runtime taking precedence
                merged_step_params = {
                    **current_step_params,
                    **step_runtime_params,
                }

                # Create updated step config
                updated_config = step_config.config.model_copy(
                    update={"parameters": merged_step_params}
                )
                updated_step_config = step_config.model_copy(
                    update={"config": updated_config}
                )
                updated_step_configs[step_name] = updated_step_config

                logger.debug(
                    f"Injected parameters for step '{step_name}': {list(step_runtime_params.keys())}"
                )
            else:
                # Keep original step config if no parameters to inject
                updated_step_configs[step_name] = step_config
        
        # Create new deployment with updated step configurations
        return deployment.model_copy(
            update={"step_configurations": updated_step_configs}
        )

    def _get_step_signature(self, step_spec: Any) -> set:
        """Extract parameter names from step function signature.

        Args:
            step_spec: The step specification containing function metadata

        Returns:
            Set of parameter names that the step function accepts
        """
        try:
            # Get step function signature from spec
            if hasattr(step_spec, "inputs"):
                # Extract parameter names from step inputs
                return set(step_spec.inputs.keys())
            else:
                logger.debug("Step spec has no inputs attribute")
                return set()
        except Exception as e:
            logger.warning(f"Could not extract step signature: {e}")
            return set()

    def _detect_parameter_conflicts(
        self, config_params: Dict[str, Any], runtime_params: Dict[str, Any]
    ) -> Dict[str, tuple]:
        """Detect conflicts between configuration and runtime parameters.

        Args:
            config_params: Parameters from step configuration
            runtime_params: Parameters provided at runtime

        Returns:
            Dictionary of conflicts mapping parameter name to (config_value, runtime_value)
        """
        conflicts = {}
        for param_name, runtime_value in runtime_params.items():
            if param_name in config_params:
                config_value = config_params[param_name]
                if config_value != runtime_value:
                    conflicts[param_name] = (config_value, runtime_value)
        return conflicts
