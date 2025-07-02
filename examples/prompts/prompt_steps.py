#!/usr/bin/env python3
#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Example ZenML steps for prompt execution and analytics."""

import time
from typing import Any, Dict, List, Optional, Tuple

from zenml import step
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.logger import get_logger

from zenml.prompts.prompt import Prompt
from zenml.prompts.prompt_analytics import get_analytics_manager

logger = get_logger(__name__)


@step
def prompt_execution_step(
    prompt: Prompt,
    input_data: Dict[str, Any],
    model_name: str = "gpt-3.5-turbo",
    track_analytics: bool = True,
    ab_test_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Execute a prompt with input data and return response with metadata.
    
    This step can be used in ZenML pipelines to execute prompts and track
    performance analytics automatically.
    
    Args:
        prompt: The Prompt artifact to execute
        input_data: Variables to substitute in the prompt template
        model_name: Name of the language model to use
        track_analytics: Whether to track execution analytics
        ab_test_id: ID of A/B test if this execution is part of one
        user_id: User ID for A/B test assignment
        
    Returns:
        Tuple of (model_response, execution_metadata)
    """
    logger.info(f"Executing prompt {prompt.prompt_id} with model {model_name}")
    
    start_time = time.time()
    
    try:
        # Format the prompt with input data
        formatted_prompt = prompt.format(**input_data)
        logger.info(f"Formatted prompt: {formatted_prompt[:200]}...")
        
        # Mock model execution - in real use, this would call actual LLM APIs
        # Users would replace this with their preferred LLM client
        response = _mock_model_execution(formatted_prompt, model_name)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Create execution metadata
        execution_metadata = {
            "prompt_id": prompt.prompt_id,
            "model_name": model_name,
            "execution_time_ms": execution_time_ms,
            "input_variables": input_data,
            "formatted_prompt": formatted_prompt,
            "success": True,
            "timestamp": time.time()
        }
        
        # Track analytics if enabled
        if track_analytics:
            analytics_manager = get_analytics_manager()
            execution_record = analytics_manager.log_execution(
                prompt_id=prompt.prompt_id or "unknown",
                input_variables=input_data,
                formatted_prompt=formatted_prompt,
                response=response,
                execution_time_ms=execution_time_ms,
                prompt_version=prompt.version,
                model_name=model_name,
                user_id=user_id,
                ab_test_id=ab_test_id,
                success=True
            )
            execution_metadata["execution_id"] = execution_record.execution_id
        
        logger.info(f"Prompt execution completed in {execution_time_ms:.2f}ms")
        
        return response, execution_metadata
        
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        
        logger.error(f"Prompt execution failed: {str(e)}")
        
        # Track failed execution
        if track_analytics:
            analytics_manager = get_analytics_manager()
            analytics_manager.log_execution(
                prompt_id=prompt.prompt_id or "unknown",
                input_variables=input_data,
                formatted_prompt=prompt.template,
                execution_time_ms=execution_time_ms,
                model_name=model_name,
                success=False,
                error_message=str(e),
                user_id=user_id,
                ab_test_id=ab_test_id
            )
        
        raise


@step
def batch_prompt_execution_step(
    prompt: Prompt,
    batch_inputs: List[Dict[str, Any]],
    model_name: str = "gpt-3.5-turbo",
    track_analytics: bool = True,
    max_parallel: int = 5,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Execute a prompt with multiple input sets in batch.
    
    Args:
        prompt: The Prompt artifact to execute
        batch_inputs: List of input variable dictionaries
        model_name: Name of the language model to use
        track_analytics: Whether to track execution analytics
        max_parallel: Maximum number of parallel executions
        
    Returns:
        List of (response, metadata) tuples
    """
    import concurrent.futures
    
    logger.info(f"Executing prompt {prompt.prompt_id} with {len(batch_inputs)} inputs")
    
    def execute_single(input_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        return prompt_execution_step(
            prompt=prompt,
            input_data=input_data,
            model_name=model_name,
            track_analytics=track_analytics
        )
    
    results = []
    
    # Use ThreadPoolExecutor for parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
        future_to_input = {
            executor.submit(execute_single, input_data): input_data 
            for input_data in batch_inputs
        }
        
        for future in concurrent.futures.as_completed(future_to_input):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Batch execution failed for input: {e}")
                # Add error result
                results.append(("", {"error": str(e), "success": False}))
    
    logger.info(f"Batch execution completed: {len(results)} results")
    return results


@step
def prompt_from_external_artifact_step(
    prompt_artifact_id: str,
    input_data: Dict[str, Any],
    model_name: str = "gpt-3.5-turbo",
) -> Tuple[str, Dict[str, Any]]:
    """Load a prompt from an external artifact and execute it.
    
    This demonstrates how to use ExternalArtifact to load prompts
    from previous pipeline runs or shared repositories.
    
    Args:
        prompt_artifact_id: ID of the external prompt artifact
        input_data: Variables to substitute in the prompt template
        model_name: Name of the language model to use
        
    Returns:
        Tuple of (model_response, execution_metadata)
    """
    # Load prompt from external artifact
    external_prompt = ExternalArtifact(id=prompt_artifact_id)
    
    # The external artifact should contain a Prompt object
    # In practice, this would be loaded and deserialized
    logger.info(f"Loading prompt from external artifact: {prompt_artifact_id}")
    
    # For demonstration, we'll create a simple prompt
    # In real usage, this would be the actual loaded prompt
    prompt = Prompt(
        template="External prompt: {query}",
        variables={"query": "default"},
        prompt_id=prompt_artifact_id
    )
    
    return prompt_execution_step(
        prompt=prompt,
        input_data=input_data,
        model_name=model_name,
        track_analytics=True
    )


@step
def prompt_analytics_aggregation_step(
    prompt_id: str,
    days_back: int = 7
) -> Dict[str, Any]:
    """Aggregate analytics for a specific prompt.
    
    Args:
        prompt_id: ID of the prompt to analyze
        days_back: Number of days to look back for analytics
        
    Returns:
        Analytics summary dictionary
    """
    from datetime import datetime, timedelta
    
    logger.info(f"Aggregating analytics for prompt {prompt_id}")
    
    analytics_manager = get_analytics_manager()
    
    # Get analytics for the specified period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    analytics = analytics_manager.get_analytics(
        prompt_id=prompt_id,
        start_date=start_date,
        end_date=end_date
    )
    
    if analytics:
        return {
            "prompt_id": analytics.prompt_id,
            "period_days": days_back,
            "total_executions": analytics.total_executions,
            "success_rate": analytics.successful_executions / analytics.total_executions if analytics.total_executions > 0 else 0,
            "avg_execution_time_ms": analytics.avg_execution_time_ms,
            "avg_quality_score": analytics.avg_quality_score,
            "total_cost_usd": analytics.total_cost_usd,
            "top_errors": analytics.top_errors[:3],  # Top 3 errors
        }
    else:
        return {
            "prompt_id": prompt_id,
            "period_days": days_back,
            "total_executions": 0,
            "message": "No analytics data found"
        }


def _mock_model_execution(prompt: str, model_name: str) -> str:
    """Mock model execution for demonstration purposes.
    
    In real usage, this would be replaced with actual LLM API calls
    like OpenAI, Anthropic, Hugging Face, etc.
    
    Args:
        prompt: Formatted prompt text
        model_name: Name of the model to use
        
    Returns:
        Mock response from the model
    """
    import hashlib
    import time
    
    # Simulate processing time
    time.sleep(0.1)
    
    # Generate a deterministic but varied response based on prompt content
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    
    responses = [
        f"This is a mock response from {model_name} for prompt hash {prompt_hash}.",
        f"Generated by {model_name}: The answer is 42. (Hash: {prompt_hash})",
        f"{model_name} response: Understanding your query about {prompt[:50]}...",
        f"Mock {model_name} output: Processing complete. Reference: {prompt_hash}",
    ]
    
    # Select response based on hash
    response_index = int(prompt_hash, 16) % len(responses)
    return responses[response_index]