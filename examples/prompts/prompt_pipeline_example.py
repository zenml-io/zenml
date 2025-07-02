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
"""Example pipeline demonstrating prompt management and analytics in ZenML."""

from typing import Dict, List, Tuple
from zenml import pipeline, step
from zenml.logger import get_logger

from zenml.prompts.prompt import Prompt
from prompt_steps import (
    prompt_execution_step,
    batch_prompt_execution_step,
    prompt_analytics_aggregation_step
)

logger = get_logger(__name__)


@step
def create_prompt_step() -> Prompt:
    """Create and return a prompt for downstream steps."""
    
    prompt = Prompt(
        name="Customer Support Response",
        template="""You are a helpful customer support representative.
        
Customer Query: {customer_query}
Product: {product_name}
Priority: {priority_level}

Please provide a helpful and professional response addressing the customer's concern.
Be specific to the product mentioned and match the urgency of the priority level.

Response:""",
        variables={
            "customer_query": "How do I reset my password?",
            "product_name": "ZenML Cloud",
            "priority_level": "medium"
        },
        prompt_type="customer_support",
        task="response_generation",
        model_config_params={
            "temperature": 0.7,
            "max_tokens": 200
        },
        description="Template for generating customer support responses"
    )
    
    logger.info(f"Created prompt: {prompt.name} (ID: {prompt.prompt_id})")
    return prompt


@step
def prepare_test_data_step() -> List[Dict[str, str]]:
    """Prepare test data for batch prompt execution."""
    
    test_cases = [
        {
            "customer_query": "I can't login to my account",
            "product_name": "ZenML Cloud",
            "priority_level": "high"
        },
        {
            "customer_query": "How do I create a new pipeline?",
            "product_name": "ZenML",
            "priority_level": "low"
        },
        {
            "customer_query": "My pipeline failed with an error",
            "product_name": "ZenML",
            "priority_level": "high"
        },
        {
            "customer_query": "Can I integrate with AWS?",
            "product_name": "ZenML",
            "priority_level": "medium"
        },
        {
            "customer_query": "Billing question about my subscription",
            "product_name": "ZenML Cloud",
            "priority_level": "medium"
        }
    ]
    
    logger.info(f"Prepared {len(test_cases)} test cases")
    return test_cases


@step
def analyze_results_step(
    batch_results: List[Tuple[str, Dict[str, any]]],
    analytics_summary: Dict[str, any]
) -> Dict[str, any]:
    """Analyze the batch execution results and combine with analytics."""
    
    successful_responses = [
        result for result in batch_results 
        if result[1].get("success", True)
    ]
    
    failed_responses = [
        result for result in batch_results 
        if not result[1].get("success", True)
    ]
    
    avg_execution_time = sum(
        result[1].get("execution_time_ms", 0) 
        for result in successful_responses
    ) / len(successful_responses) if successful_responses else 0
    
    analysis = {
        "total_requests": len(batch_results),
        "successful_requests": len(successful_responses),
        "failed_requests": len(failed_responses),
        "success_rate": len(successful_responses) / len(batch_results) if batch_results else 0,
        "avg_execution_time_ms": avg_execution_time,
        "sample_responses": [result[0][:100] + "..." for result in successful_responses[:3]],
        "analytics_summary": analytics_summary
    }
    
    logger.info(f"Analysis complete: {analysis['success_rate']:.2%} success rate")
    return analysis


@pipeline
def prompt_analytics_pipeline() -> Dict[str, any]:
    """Pipeline demonstrating prompt execution and analytics tracking."""
    
    # Step 1: Create a prompt
    prompt = create_prompt_step()
    
    # Step 2: Prepare test data
    test_data = prepare_test_data_step()
    
    # Step 3: Execute prompt with batch data
    batch_results = batch_prompt_execution_step(
        prompt=prompt,
        batch_inputs=test_data,
        model_name="gpt-3.5-turbo",
        track_analytics=True,
        max_parallel=3
    )
    
    # Step 4: Get analytics summary (this would work after some executions)
    analytics_summary = prompt_analytics_aggregation_step(
        prompt_id=prompt.prompt_id,
        days_back=1  # Look at recent data
    )
    
    # Step 5: Analyze results
    final_analysis = analyze_results_step(
        batch_results=batch_results,
        analytics_summary=analytics_summary
    )
    
    return final_analysis


@pipeline 
def prompt_ab_testing_pipeline() -> Dict[str, any]:
    """Pipeline demonstrating A/B testing with prompts."""
    
    # Create control prompt
    control_prompt = Prompt(
        name="Control Prompt",
        template="Answer this question: {question}",
        prompt_type="qa"
    )
    
    # Create variant prompt with different style
    variant_prompt = Prompt(
        name="Variant Prompt", 
        template="Think step by step and answer: {question}\n\nStep 1:",
        prompt_type="qa"
    )
    
    # Create A/B test
    ab_test = control_prompt.create_ab_test(
        variant_prompts={"step_by_step": variant_prompt},
        test_name="QA Style Comparison",
        duration_days=3,
        primary_metric="quality_score"
    )
    
    logger.info(f"Created A/B test: {ab_test.test_id}")
    
    # This would be followed by actual execution steps using the A/B test
    return {"ab_test_id": ab_test.test_id, "status": "created"}


if __name__ == "__main__":
    # Run the main pipeline
    print("Running prompt analytics pipeline...")
    result = prompt_analytics_pipeline()
    print(f"Pipeline completed: {result}")
    
    print("\nRunning A/B testing pipeline...")
    ab_result = prompt_ab_testing_pipeline()
    print(f"A/B test created: {ab_result}")