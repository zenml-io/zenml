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

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from zenml.logger import get_logger
from zenml.orchestrators.topsort import topsorted_layers
from zenml.steps.step_context import StepContext
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse
    from zenml.steps import BaseStep

logger = get_logger(__name__)


class ServingStepContext:
    """Lightweight step context for serving scenarios.
    
    This provides a minimal implementation of step context functionality
    without the overhead of the full ZenML context system.
    """
    
    def __init__(self, step_name: str):
        """Initialize serving step context.
        
        Args:
            step_name: Name of the step being executed
        """
        self.step_name = step_name
        self._metadata = {}
    
    def add_output_metadata(self, metadata: Dict[str, Any]) -> None:
        """Add metadata for step outputs (no-op in serving).
        
        Args:
            metadata: Metadata to add
        """
        self._metadata.update(metadata)
        logger.debug(f"Serving metadata (not stored): {metadata}")
    
    def get_output_artifact_uri(self, output_name: Optional[str] = None) -> str:
        """Get output artifact URI (mock for serving).
        
        Args:
            output_name: Name of the output
            
        Returns:
            Mock URI
        """
        return f"mock://serving/{self.step_name}/{output_name or 'output'}"
    
    @property
    def step_run_info(self):
        """Mock step run info."""
        return None
    
    @property
    def pipeline_run(self):
        """Mock pipeline run."""
        return None
    
    @property
    def step_run(self):
        """Mock step run."""
        return None


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
    
    def __init__(self, deployment: "PipelineDeploymentResponse",
                 pipeline_run: Optional[Any] = None):
        """Initialize the direct execution engine.
        
        Args:
            deployment: The pipeline deployment configuration
            pipeline_run: Optional pipeline run for tracking. If provided,
                steps will have proper context with run information.
        """
        self.deployment = deployment
        self.pipeline_run = pipeline_run
        self._loaded_steps: Dict[str, type] = {}
        self._execution_order: List[str] = []
        
        # Pre-load all steps and build execution order
        self._initialize_steps()
        self._build_execution_order()
        
        logger.debug(
            f"DirectExecutionEngine initialized for pipeline "
            f"'{deployment.pipeline_configuration.name}' with "
            f"{len(self._loaded_steps)} steps"
            f"{' (tracked)' if pipeline_run else ' (untracked)'}"
        )
    
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
        for step_name, step_config in self.deployment.step_configurations.items():
            try:
                # Load the step class from its source
                step_source = step_config.spec.source
                logger.debug(f"Loading step '{step_name}' from source: {step_source}")
                
                # Use source_utils to load the step class
                step_class = source_utils.load(step_source)
                
                # Store the step class (don't instantiate yet)
                # We'll instantiate it during execution with proper parameters
                self._loaded_steps[step_name] = step_class
                logger.debug(f"Successfully loaded step '{step_name}'")
                
            except Exception as e:
                logger.error(f"Failed to load step '{step_name}': {str(e)}")
                raise RuntimeError(
                    f"Failed to initialize step '{step_name}': {str(e)}"
                ) from e
    
    def _build_execution_order(self) -> None:
        """Build the execution order based on step dependencies.
        
        This creates a topological sort of the steps based on their
        input/output relationships using ZenML's existing topsort implementation.
        """
        # Build a DAG (Directed Acyclic Graph) from step dependencies
        dag: Dict[str, List[str]] = {}
        
        for step_name, step_config in self.deployment.step_configurations.items():
            upstream_steps = []
            
            # Find upstream steps from input specifications
            for input_name, input_spec in step_config.spec.inputs.items():
                # Check if this input comes from another step
                if hasattr(input_spec, "step_name") and input_spec.step_name:
                    if input_spec.step_name != "pipeline":  # Not a pipeline parameter
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
    
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the pipeline with direct data passing.
        
        This method executes all pipeline steps in order, passing data
        directly between steps without any serialization or storage.
        
        Args:
            parameters: Input parameters for the pipeline
            
        Returns:
            The output of the final pipeline step
            
        Raises:
            RuntimeError: If step execution fails
        """
        start_time = time.time()
        
        # Track outputs from each step
        step_outputs: Dict[str, Any] = {}
        
        # Add pipeline parameters to step outputs for downstream access
        step_outputs["pipeline"] = parameters
        
        # Also add parameters directly to step_outputs for easy access
        step_outputs.update(parameters)
        
        # Execute each step in order
        for step_name in self._execution_order:
            step_start_time = time.time()
            
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
                
                # Execute the step
                output = self._execute_step(
                    step_name, step_class, step_inputs
                )
                
                # Store output for downstream steps
                step_outputs[step_name] = output
                
                step_duration = time.time() - step_start_time
                logger.info(
                    f"Step '{step_name}' completed in {step_duration:.3f}s"
                )
                
            except Exception as e:
                logger.error(f"Step '{step_name}' failed: {str(e)}")
                raise RuntimeError(
                    f"Pipeline execution failed at step '{step_name}': {str(e)}"
                ) from e
        
        # Get the output from the last step
        final_output = step_outputs.get(self._execution_order[-1])
        
        total_duration = time.time() - start_time
        logger.info(
            f"Pipeline execution completed in {total_duration:.3f}s"
        )
        
        return final_output
    
    def _resolve_step_inputs(
        self,
        step_name: str,
        step_config: "Step",
        step_outputs: Dict[str, Any],
        parameters: Dict[str, Any]
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
            
            logger.debug(f"Resolving input '{input_name}' from step '{source_step_name}' output '{output_name}'")
            
            if source_step_name in step_outputs:
                try:
                    resolved_value = self._resolve_step_output_value(
                        source_step_name=source_step_name,
                        output_name=output_name,
                        step_output=step_outputs[source_step_name],
                    )
                    input_artifacts[input_name] = resolved_value
                    logger.debug(f"✅ Resolved '{input_name}' from step '{source_step_name}' output '{output_name}'")
                except Exception as e:
                    logger.error(f"❌ Failed to resolve input '{input_name}': {e}")
                    raise RuntimeError(f"Cannot resolve input '{input_name}' for step '{step_name}': {e}")
            else:
                logger.warning(f"❌ Source step '{source_step_name}' not found for input '{input_name}'")
        
        # Step 2: Get step function arguments using proper inspection
        step_class = self._loaded_steps.get(step_name)
        if not step_class or not hasattr(step_class, "entrypoint"):
            logger.error(f"Step class or entrypoint not found for '{step_name}'")
            return {}
        
        import inspect
        try:
            # Use getfullargspec like ZenML's StepRunner does
            spec = inspect.getfullargspec(inspect.unwrap(step_class.entrypoint))
            function_args = spec.args
            
            # Remove 'self' if present
            if function_args and function_args[0] == "self":
                function_args = function_args[1:]
                
            logger.debug(f"Step function arguments: {function_args}")
            
        except Exception as e:
            logger.error(f"Failed to get function arguments for step '{step_name}': {e}")
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
                logger.error(f"❌ Unable to resolve function argument '{arg_name}' for step '{step_name}'")
                logger.error(f"Available input artifacts: {list(input_artifacts.keys())}")
                logger.error(f"Available parameters: {list(all_parameters.keys())}")
                # This should cause the step to fail, matching ZenML's behavior
                raise RuntimeError(f"Unable to find value for step function argument `{arg_name}`.")
        
        return function_params
    
    def _resolve_step_output_value(
        self,
        source_step_name: str, 
        output_name: str, 
        step_output: Any, 
    ) -> Any:
        """Properly resolve step output value based on ZenML output specifications.
        
        This method handles the different ways ZenML steps can return outputs:
        1. Single output: step returns the value directly
        2. Multiple named outputs: step returns dict {"output1": val1, "output2": val2}
        3. Multiple positional outputs: step returns tuple (val1, val2, val3)
        
        Args:
            source_step_name: Name of the step that produced the output
            output_name: Name of the specific output we want to extract
            step_output: The actual output data from the step
            
        Returns:
            The resolved output value
            
        Raises:
            ValueError: If output cannot be resolved properly
        """
        # Get the source step's output specification
        source_step_config = self.deployment.step_configurations[source_step_name]
        output_specs = source_step_config.spec.outputs
        
        logger.debug(f"Resolving output '{output_name}' from step '{source_step_name}' with {len(output_specs)} outputs")
        
        if len(output_specs) == 1:
            # Single output step - return the whole output regardless of naming
            logger.debug("Single output step - using entire output")
            return step_output
            
        elif len(output_specs) > 1:
            # Multi-output step - need to resolve correctly
            logger.debug(f"Multi-output step with outputs: {list(output_specs.keys())}")
            
            if isinstance(step_output, dict):
                # Named outputs (step returns {"model": ..., "metrics": ...})
                if output_name in step_output:
                    logger.debug(f"Found named output '{output_name}' in dict")
                    return step_output[output_name]
                else:
                    available_outputs = list(step_output.keys())
                    raise ValueError(
                        f"Output '{output_name}' not found in step '{source_step_name}' outputs. "
                        f"Available outputs: {available_outputs}"
                    )
                    
            elif isinstance(step_output, (tuple, list)):
                # Positional outputs (step returns (model, metrics))
                output_names = list(output_specs.keys())
                logger.debug(f"Resolving positional output '{output_name}' from {output_names}")
                
                try:
                    output_index = output_names.index(output_name)
                    if output_index < len(step_output):
                        logger.debug(f"Found positional output '{output_name}' at index {output_index}")
                        return step_output[output_index]
                    else:
                        raise IndexError(f"Output index {output_index} out of range")
                except ValueError:
                    raise ValueError(
                        f"Output '{output_name}' not found in step '{source_step_name}' output specification. "
                        f"Expected outputs: {output_names}"
                    )
                except IndexError as e:
                    raise ValueError(
                        f"Step '{source_step_name}' returned {len(step_output)} values but "
                        f"specification expects {len(output_names)} outputs: {e}"
                    )
            else:
                # Single value but multiple outputs expected - this is likely an error
                raise ValueError(
                    f"Step '{source_step_name}' has {len(output_specs)} output specifications "
                    f"but returned a single value of type {type(step_output).__name__}. "
                    f"Expected either a dict with keys {list(output_specs.keys())} "
                    f"or a tuple/list with {len(output_specs)} values."
                )
        else:
            # No outputs specified - this shouldn't happen
            raise ValueError(f"Step '{source_step_name}' has no output specifications")

    def _execute_step(
        self,
        step_name: str,
        step_class: type,
        inputs: Dict[str, Any]
    ) -> Any:
        """Execute a single step with given inputs.
        
        This method handles the actual step execution, including setting up
        the step context and calling the step's entrypoint.
        
        TODO: CRITICAL THREAD SAFETY ISSUE - MUST FIX BEFORE PRODUCTION
        =============================================================
        
        The current implementation has dangerous race conditions when handling
        concurrent requests. The global state modification below causes requests
        to interfere with each other's context.
        
        PROBLEM:
        - StepContext._clear() affects ALL requests globally
        - context_module.get_step_context monkey patching creates race conditions
        - Concurrent requests overwrite each other's context
        
        SOLUTION:
        Use Python's contextvars for thread-safe context management.
        See detailed implementation in /THREAD_SAFETY_FIX.md
        
        IMPACT:
        - Current: Concurrent requests return wrong results or crash
        - After fix: Each request has isolated, thread-safe context
        
        PRIORITY: CRITICAL - Must implement before production deployment
        
        Args:
            step_name: Name of the step being executed
            step_class: The step class to instantiate and execute
            inputs: Input data for the step
            
        Returns:
            The output of the step execution
        """
        # Clear any existing context
        StepContext._clear()
        
        # Set up a lightweight serving context
        serving_context = ServingStepContext(step_name)
        
        # Monkey patch the get_step_context function temporarily
        import zenml.steps.step_context as context_module
        original_get_context = context_module.get_step_context
        
        def mock_get_step_context():
            return serving_context
        
        context_module.get_step_context = mock_get_step_context
        
        try:
            # Get the entrypoint function directly from the step class and call it
            logger.debug(f"Executing step '{step_name}' with inputs: {inputs}")
            entrypoint_func = step_class.entrypoint
            result = entrypoint_func(**inputs)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing step '{step_name}': {str(e)}")
            raise
            
        finally:
            # Restore original context function and clean up
            context_module.get_step_context = original_get_context
            StepContext._clear()
    
    
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