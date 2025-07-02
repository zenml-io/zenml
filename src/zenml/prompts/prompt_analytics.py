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
"""Prompt Analytics and A/B Testing functionality."""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field


class PromptExecution(BaseModel):
    """Represents a single prompt execution for analytics."""
    
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt_id: str
    prompt_version: Optional[str] = None
    model_name: Optional[str] = None
    
    # Execution details
    input_variables: Dict[str, Any]
    formatted_prompt: str
    response: Optional[str] = None
    
    # Performance metrics
    execution_time_ms: Optional[float] = None
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Quality metrics
    quality_score: Optional[float] = None  # 0-1 scale
    user_rating: Optional[int] = None  # 1-5 scale
    success: bool = True
    error_message: Optional[str] = None
    
    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    pipeline_run_id: Optional[str] = None
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # A/B testing
    ab_test_group: Optional[str] = None
    ab_test_id: Optional[str] = None


class ABTestConfiguration(BaseModel):
    """Configuration for A/B testing prompts."""
    
    test_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    
    # Test variants
    variants: Dict[str, str] = Field(
        description="Mapping of variant names to prompt IDs"
    )
    
    # Traffic allocation (should sum to 1.0)
    traffic_allocation: Dict[str, float] = Field(
        description="Percentage of traffic for each variant"
    )
    
    # Test parameters
    start_date: datetime
    end_date: Optional[datetime] = None
    min_sample_size: int = Field(default=100, description="Minimum samples per variant")
    confidence_level: float = Field(default=0.95, description="Statistical confidence level")
    
    # Success metrics
    primary_metric: str = Field(
        default="quality_score",
        description="Primary metric to optimize: quality_score, execution_time_ms, cost_usd"
    )
    secondary_metrics: List[str] = Field(
        default_factory=list,
        description="Additional metrics to track"
    )
    
    # Status
    status: str = Field(default="draft", description="draft, running, completed, paused")
    winner: Optional[str] = Field(default=None, description="Winning variant if test completed")
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptAnalytics(BaseModel):
    """Analytics aggregations for prompts."""
    
    prompt_id: str
    period_start: datetime
    period_end: datetime
    
    # Execution counts
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    
    # Performance metrics
    avg_execution_time_ms: Optional[float] = None
    p95_execution_time_ms: Optional[float] = None
    avg_quality_score: Optional[float] = None
    avg_user_rating: Optional[float] = None
    
    # Cost metrics
    total_cost_usd: Optional[float] = None
    avg_cost_per_execution: Optional[float] = None
    
    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_input_tokens: Optional[float] = None
    avg_output_tokens: Optional[float] = None
    
    # Quality trends
    quality_trend: Optional[str] = None  # "improving", "declining", "stable"
    performance_trend: Optional[str] = None
    
    # Top error categories
    top_errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Usage patterns
    peak_usage_hours: List[int] = Field(default_factory=list)
    most_common_variables: Dict[str, int] = Field(default_factory=dict)


class PromptAnalyticsManager:
    """Manager for prompt analytics and A/B testing."""
    
    def __init__(self):
        self._executions: List[PromptExecution] = []
        self._ab_tests: Dict[str, ABTestConfiguration] = {}
    
    def log_execution(
        self,
        prompt_id: str,
        input_variables: Dict[str, Any],
        formatted_prompt: str,
        response: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        quality_score: Optional[float] = None,
        **kwargs: Any
    ) -> PromptExecution:
        """Log a prompt execution for analytics.
        
        Args:
            prompt_id: ID of the prompt that was executed
            input_variables: Variables used to format the prompt
            formatted_prompt: The final formatted prompt text
            response: Response from the model
            execution_time_ms: Time taken to execute in milliseconds
            quality_score: Quality score of the response (0-1)
            **kwargs: Additional execution metadata
            
        Returns:
            The logged execution record
        """
        execution = PromptExecution(
            prompt_id=prompt_id,
            input_variables=input_variables,
            formatted_prompt=formatted_prompt,
            response=response,
            execution_time_ms=execution_time_ms,
            quality_score=quality_score,
            **kwargs
        )
        
        self._executions.append(execution)
        return execution
    
    def create_ab_test(
        self,
        name: str,
        variants: Dict[str, str],
        traffic_allocation: Optional[Dict[str, float]] = None,
        duration_days: int = 7,
        **kwargs: Any
    ) -> ABTestConfiguration:
        """Create a new A/B test configuration.
        
        Args:
            name: Name of the A/B test
            variants: Dictionary mapping variant names to prompt IDs
            traffic_allocation: Traffic allocation per variant (defaults to equal)
            duration_days: How long to run the test
            **kwargs: Additional test configuration
            
        Returns:
            The created A/B test configuration
        """
        if traffic_allocation is None:
            # Equal allocation across all variants
            allocation = 1.0 / len(variants)
            traffic_allocation = {variant: allocation for variant in variants}
        
        # Validate traffic allocation sums to 1.0
        total_allocation = sum(traffic_allocation.values())
        if abs(total_allocation - 1.0) > 0.001:
            raise ValueError(f"Traffic allocation must sum to 1.0, got {total_allocation}")
        
        test_config = ABTestConfiguration(
            name=name,
            variants=variants,
            traffic_allocation=traffic_allocation,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=duration_days),
            **kwargs
        )
        
        self._ab_tests[test_config.test_id] = test_config
        return test_config
    
    def select_variant(self, test_id: str, user_id: Optional[str] = None) -> str:
        """Select a variant for a user in an A/B test.
        
        Args:
            test_id: ID of the A/B test
            user_id: ID of the user (for consistent assignment)
            
        Returns:
            Selected variant name
        """
        if test_id not in self._ab_tests:
            raise ValueError(f"A/B test {test_id} not found")
        
        test_config = self._ab_tests[test_id]
        
        if test_config.status != "running":
            raise ValueError(f"A/B test {test_id} is not running (status: {test_config.status})")
        
        # Use user_id for consistent assignment, or random for anonymous users
        if user_id:
            # Hash user_id + test_id for consistent but randomized assignment
            import hashlib
            hash_input = f"{user_id}:{test_id}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            random_value = (hash_value % 10000) / 10000.0
        else:
            import random
            random_value = random.random()
        
        # Select variant based on traffic allocation
        cumulative_allocation = 0.0
        for variant, allocation in test_config.traffic_allocation.items():
            cumulative_allocation += allocation
            if random_value <= cumulative_allocation:
                return variant
        
        # Fallback to first variant if something goes wrong
        return list(test_config.variants.keys())[0]
    
    def get_analytics(
        self,
        prompt_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PromptAnalytics:
        """Get analytics for a specific prompt.
        
        Args:
            prompt_id: ID of the prompt to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Analytics summary for the prompt
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Filter executions for this prompt and time period
        filtered_executions = [
            exec for exec in self._executions
            if exec.prompt_id == prompt_id 
            and start_date <= exec.timestamp <= end_date
        ]
        
        if not filtered_executions:
            return PromptAnalytics(
                prompt_id=prompt_id,
                period_start=start_date,
                period_end=end_date
            )
        
        # Calculate metrics
        total_executions = len(filtered_executions)
        successful_executions = sum(1 for exec in filtered_executions if exec.success)
        failed_executions = total_executions - successful_executions
        
        # Performance metrics
        execution_times = [exec.execution_time_ms for exec in filtered_executions if exec.execution_time_ms]
        quality_scores = [exec.quality_score for exec in filtered_executions if exec.quality_score]
        user_ratings = [exec.user_rating for exec in filtered_executions if exec.user_rating]
        costs = [exec.cost_usd for exec in filtered_executions if exec.cost_usd]
        
        avg_execution_time_ms = sum(execution_times) / len(execution_times) if execution_times else None
        p95_execution_time_ms = None
        if execution_times:
            sorted_times = sorted(execution_times)
            p95_index = int(0.95 * len(sorted_times))
            p95_execution_time_ms = sorted_times[p95_index]
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
        avg_user_rating = sum(user_ratings) / len(user_ratings) if user_ratings else None
        total_cost_usd = sum(costs) if costs else None
        avg_cost_per_execution = total_cost_usd / total_executions if total_cost_usd else None
        
        # Token metrics
        input_tokens = [exec.token_count_input for exec in filtered_executions if exec.token_count_input]
        output_tokens = [exec.token_count_output for exec in filtered_executions if exec.token_count_output]
        
        total_input_tokens = sum(input_tokens) if input_tokens else 0
        total_output_tokens = sum(output_tokens) if output_tokens else 0
        avg_input_tokens = total_input_tokens / len(input_tokens) if input_tokens else None
        avg_output_tokens = total_output_tokens / len(output_tokens) if output_tokens else None
        
        # Error analysis
        errors = [exec.error_message for exec in filtered_executions if exec.error_message]
        error_counts = {}
        for error in errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        
        top_errors = [
            {"error": error, "count": count}
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return PromptAnalytics(
            prompt_id=prompt_id,
            period_start=start_date,
            period_end=end_date,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            avg_execution_time_ms=avg_execution_time_ms,
            p95_execution_time_ms=p95_execution_time_ms,
            avg_quality_score=avg_quality_score,
            avg_user_rating=avg_user_rating,
            total_cost_usd=total_cost_usd,
            avg_cost_per_execution=avg_cost_per_execution,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
            top_errors=top_errors
        )
    
    def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get results for an A/B test.
        
        Args:
            test_id: ID of the A/B test
            
        Returns:
            Dictionary containing test results and statistical analysis
        """
        if test_id not in self._ab_tests:
            raise ValueError(f"A/B test {test_id} not found")
        
        test_config = self._ab_tests[test_id]
        
        # Get executions for each variant
        variant_results = {}
        for variant_name, prompt_id in test_config.variants.items():
            variant_executions = [
                exec for exec in self._executions
                if exec.ab_test_id == test_id and exec.ab_test_group == variant_name
            ]
            
            if variant_executions:
                # Calculate metrics for this variant
                quality_scores = [exec.quality_score for exec in variant_executions if exec.quality_score]
                execution_times = [exec.execution_time_ms for exec in variant_executions if exec.execution_time_ms]
                
                variant_results[variant_name] = {
                    "sample_size": len(variant_executions),
                    "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
                    "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else None,
                    "success_rate": sum(1 for exec in variant_executions if exec.success) / len(variant_executions)
                }
            else:
                variant_results[variant_name] = {
                    "sample_size": 0,
                    "avg_quality_score": None,
                    "avg_execution_time": None,
                    "success_rate": 0.0
                }
        
        # Determine if test has statistical significance (simplified)
        min_samples_met = all(
            result["sample_size"] >= test_config.min_sample_size
            for result in variant_results.values()
        )
        
        # Find best performing variant based on primary metric
        best_variant = None
        best_score = None
        
        for variant_name, results in variant_results.items():
            if test_config.primary_metric == "quality_score" and results["avg_quality_score"]:
                score = results["avg_quality_score"]
            elif test_config.primary_metric == "execution_time_ms" and results["avg_execution_time"]:
                score = -results["avg_execution_time"]  # Lower is better
            else:
                score = results["success_rate"]
            
            if best_score is None or (score and score > best_score):
                best_score = score
                best_variant = variant_name
        
        return {
            "test_config": test_config,
            "variant_results": variant_results,
            "statistical_significance": min_samples_met,
            "recommended_winner": best_variant,
            "confidence_level": test_config.confidence_level if min_samples_met else None
        }


# Global analytics manager instance
_analytics_manager = PromptAnalyticsManager()


def get_analytics_manager() -> PromptAnalyticsManager:
    """Get the global prompt analytics manager."""
    return _analytics_manager