"""
Comprehensive ZenML Prompt Management Pipelines

This module contains the complete demonstration pipelines showcasing:
1. End-to-end prompt lifecycle management
2. LLM-as-Judge evaluation framework
3. A/B testing with real LLM responses using LiteLLM
4. Production deployment and monitoring
"""

from typing import Dict, List, Any, Tuple, Annotated
from zenml import pipeline, step, Model
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.logger import get_logger

# Import our custom steps
from steps.advanced_prompt_creation import (
    create_customer_service_prompts,
    create_content_generation_prompts,
    create_code_assistant_prompts
)
from steps.litellm_integration import (
    generate_llm_responses,
    batch_evaluate_responses
)
from steps.advanced_evaluation import (
    llm_judge_comprehensive_evaluation,
    statistical_comparison_analysis,
    performance_benchmarking
)
from steps.production_steps import (
    deploy_best_prompt,
    monitor_production_performance,
    trigger_retraining_if_needed
)

logger = get_logger(__name__)


@step
def showcase_prompt_capabilities() -> Dict[str, Any]:
    """Demonstrate ZenML's comprehensive prompt management capabilities."""
    
    capabilities = {
        "prompt_management": {
            "versioning": "Automatic semantic versioning with lineage tracking",
            "metadata": "Rich metadata extraction and searchability", 
            "templating": "Advanced variable substitution and validation",
            "artifact_system": "First-class artifacts with type safety"
        },
        "evaluation": {
            "llm_as_judge": "Multi-criteria automated evaluation",
            "a_b_testing": "Statistical significance testing",
            "performance_metrics": "Latency, cost, and quality tracking",
            "continuous_monitoring": "Production quality monitoring"
        },
        "integration": {
            "llm_providers": "Unified interface via LiteLLM", 
            "orchestration": "Stack-agnostic pipeline execution",
            "artifact_store": "Cloud-native artifact management",
            "model_registry": "Deployment and rollback capabilities"
        },
        "production": {
            "deployment": "Zero-downtime prompt deployment",
            "monitoring": "Real-time performance tracking",
            "alerting": "Quality degradation detection",
            "rollback": "Instant rollback to previous versions"
        }
    }
    
    logger.info("ZenML Prompt Management Capabilities Overview:")
    for category, features in capabilities.items():
        logger.info(f"\n{category.upper()}:")
        for feature, description in features.items():
            logger.info(f"  • {feature}: {description}")
    
    return capabilities


@step
def generate_evaluation_report(
    evaluations: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    performance_data: Dict[str, Any]
) -> Annotated[Dict[str, Any], ArtifactConfig(name="comprehensive_evaluation_report")]:
    """Generate a comprehensive evaluation report showcasing ZenML's capabilities."""
    
    report = {
        "executive_summary": {
            "total_prompts_evaluated": len(evaluations),
            "total_comparisons": len(comparisons),
            "evaluation_framework": "LLM-as-Judge with multi-criteria assessment",
            "statistical_significance": "95% confidence intervals",
            "zenml_advantages": [
                "Automated prompt versioning and lineage tracking",
                "Built-in LLM-as-Judge evaluation framework", 
                "Stack-agnostic LLM provider integration",
                "Production deployment with monitoring",
                "Enterprise-grade security and compliance"
            ]
        },
        "evaluation_results": evaluations,
        "comparison_analysis": comparisons,
        "performance_benchmarks": performance_data,
        "recommendations": {
            "best_performing_prompt": _identify_best_prompt(evaluations),
            "optimization_opportunities": _identify_optimizations(comparisons),
            "deployment_readiness": _assess_deployment_readiness(performance_data)
        },
        "zenml_value_proposition": {
            "vs_langsmith": [
                "✓ Complete MLOps pipeline integration vs. monitoring-only",
                "✓ Stack-agnostic deployment vs. vendor lock-in",
                "✓ Built-in evaluation framework vs. external tools needed"
            ],
            "vs_promptlayer": [
                "✓ End-to-end pipeline orchestration vs. logging-only",
                "✓ Production deployment capabilities vs. development focus",
                "✓ Enterprise security and compliance vs. basic tracking"
            ],
            "vs_weights_biases": [
                "✓ LLM-specific workflow optimization vs. general ML tracking", 
                "✓ Prompt-as-code version control vs. manual tracking",
                "✓ Automated evaluation pipelines vs. manual analysis"
            ]
        }
    }
    
    logger.info("📊 Comprehensive Evaluation Report Generated")
    logger.info(f"Evaluated {len(evaluations)} prompts across {len(comparisons)} comparisons")
    
    return report


def _identify_best_prompt(evaluations: List[Dict[str, Any]]) -> str:
    """Identify the best performing prompt from evaluations."""
    if not evaluations:
        return "No evaluations available"
    
    best_prompt = max(evaluations, key=lambda x: x.get("overall_score", 0))
    return f"Prompt {best_prompt.get('prompt_id', 'unknown')} with score {best_prompt.get('overall_score', 0):.3f}"


def _identify_optimizations(comparisons: List[Dict[str, Any]]) -> List[str]:
    """Identify optimization opportunities from comparisons."""
    optimizations = []
    
    for comparison in comparisons:
        if comparison.get("improvement_percentage", 0) > 10:
            optimizations.append(
                f"Significant improvement opportunity: {comparison.get('improvement_percentage', 0):.1f}% gain possible"
            )
    
    return optimizations or ["All prompts performing within acceptable ranges"]


def _assess_deployment_readiness(performance_data: Dict[str, Any]) -> str:
    """Assess if prompts are ready for production deployment."""
    avg_latency = performance_data.get("average_latency", 0)
    avg_cost = performance_data.get("average_cost", 0)
    success_rate = performance_data.get("success_rate", 0)
    
    if success_rate > 0.95 and avg_latency < 2000 and avg_cost < 0.10:
        return "✅ Ready for production deployment"
    elif success_rate > 0.90:
        return "⚠️ Ready with monitoring - watch performance metrics"
    else:
        return "❌ Requires optimization before deployment"


@pipeline(
    model=Model(
        name="zenml_prompt_showcase",
        version=None,
        description="Comprehensive ZenML prompt management demonstration"
    )
)
def comprehensive_prompt_showcase():
    """
    Comprehensive pipeline showcasing ZenML's complete prompt management capabilities.
    
    This pipeline demonstrates:
    1. Prompt creation with rich metadata and versioning
    2. LLM-as-Judge evaluation with multiple criteria
    3. A/B testing with statistical significance
    4. Performance benchmarking and optimization
    5. Production deployment readiness assessment
    """
    
    # Phase 1: Showcase ZenML capabilities
    capabilities = showcase_prompt_capabilities()
    
    # Phase 2: Create diverse prompt types
    customer_service_prompts = create_customer_service_prompts()
    content_generation_prompts = create_content_generation_prompts()
    code_assistant_prompts = create_code_assistant_prompts()
    
    # Phase 3: Generate real LLM responses for evaluation
    cs_responses = generate_llm_responses(customer_service_prompts, "customer_service")
    content_responses = generate_llm_responses(content_generation_prompts, "content_generation")
    code_responses = generate_llm_responses(code_assistant_prompts, "code_assistance")
    
    # Phase 4: Comprehensive LLM-as-Judge evaluation
    cs_evaluation = llm_judge_comprehensive_evaluation(
        cs_responses, 
        ["relevance", "helpfulness", "professionalism", "accuracy"]
    )
    content_evaluation = llm_judge_comprehensive_evaluation(
        content_responses,
        ["creativity", "clarity", "engagement", "accuracy"]
    )
    code_evaluation = llm_judge_comprehensive_evaluation(
        code_responses,
        ["correctness", "efficiency", "readability", "best_practices"]
    )
    
    # Phase 5: Statistical comparison analysis
    cs_comparison = statistical_comparison_analysis(cs_evaluation, "customer_service")
    content_comparison = statistical_comparison_analysis(content_evaluation, "content_generation")
    code_comparison = statistical_comparison_analysis(code_evaluation, "code_assistance")
    
    # Phase 6: Performance benchmarking
    performance_data = performance_benchmarking([cs_responses, content_responses, code_responses])
    
    # Phase 7: Generate comprehensive report
    final_report = generate_evaluation_report(
        evaluations=[cs_evaluation, content_evaluation, code_evaluation],
        comparisons=[cs_comparison, content_comparison, code_comparison],
        performance_data=performance_data
    )


@pipeline(
    model=Model(
        name="zenml_prompt_optimization",
        version=None,
        description="Iterative prompt optimization using ZenML"
    )
)
def prompt_optimization_pipeline():
    """
    Pipeline demonstrating iterative prompt optimization.
    
    Shows how ZenML enables continuous prompt improvement through:
    1. Systematic A/B testing
    2. Performance tracking over iterations
    3. Automated prompt generation
    4. Statistical significance testing
    """
    
    # Start with baseline prompts
    baseline_prompts = create_customer_service_prompts()
    
    # Generate initial responses and evaluation
    initial_responses = generate_llm_responses(baseline_prompts, "optimization_baseline")
    initial_evaluation = llm_judge_comprehensive_evaluation(
        initial_responses,
        ["helpfulness", "accuracy", "efficiency", "user_satisfaction"]
    )
    
    # Iterative optimization (3 rounds)
    for iteration in range(1, 4):
        # Create optimized prompts based on previous results
        optimized_prompts = _create_optimized_prompts(initial_evaluation, iteration)
        
        # Test new prompts
        new_responses = generate_llm_responses(optimized_prompts, f"optimization_round_{iteration}")
        new_evaluation = llm_judge_comprehensive_evaluation(
            new_responses,
            ["helpfulness", "accuracy", "efficiency", "user_satisfaction"]
        )
        
        # Compare with baseline
        comparison = statistical_comparison_analysis(
            [initial_evaluation, new_evaluation], 
            f"optimization_iteration_{iteration}"
        )
        
        # Update baseline if improvement is significant
        if comparison.get("improvement_percentage", 0) > 5:
            initial_evaluation = new_evaluation
            logger.info(f"✅ Iteration {iteration}: {comparison.get('improvement_percentage', 0):.1f}% improvement")
        else:
            logger.info(f"⚠️ Iteration {iteration}: No significant improvement")


@step 
def _create_optimized_prompts(evaluation_data: Dict[str, Any], iteration: int) -> List[Dict[str, Any]]:
    """Create optimized prompts based on evaluation feedback."""
    # This would use the evaluation feedback to generate improved prompts
    # For demo purposes, we'll create variations with different approaches
    
    optimizations = [
        {
            "approach": "enhanced_context",
            "template": """You are an expert customer service representative with deep product knowledge.

Customer Context: {context}
Customer Question: {question}
Product Information: {product_info}
Customer History: {customer_history}

Provide a comprehensive, empathetic, and actionable response that:
1. Addresses the specific question
2. Considers the customer's context and history
3. Offers concrete next steps
4. Maintains a professional yet warm tone

Response:""",
            "metadata": {
                "optimization_round": iteration,
                "strategy": "enhanced_context_and_structure",
                "expected_improvement": "Better context awareness and structure"
            }
        },
        {
            "approach": "step_by_step",
            "template": """You are a helpful customer service assistant. Follow these steps:

Step 1: Understand the customer's situation
Customer Question: {question}
Customer Context: {context}

Step 2: Identify the core issue and any underlying concerns

Step 3: Provide a clear, step-by-step solution

Step 4: Offer additional assistance or resources if appropriate

Ensure your response is empathetic, accurate, and actionable.""",
            "metadata": {
                "optimization_round": iteration,
                "strategy": "structured_step_by_step",
                "expected_improvement": "More systematic problem solving"
            }
        }
    ]
    
    return optimizations


@pipeline(
    model=Model(
        name="zenml_prompt_production",
        version=None,
        description="Production deployment and monitoring of optimized prompts"
    )
)
def production_deployment_pipeline():
    """
    Pipeline demonstrating production deployment capabilities.
    
    Shows ZenML's enterprise-ready features:
    1. Automated deployment of best-performing prompts
    2. Real-time monitoring and alerting
    3. Automated rollback on quality degradation
    4. Continuous evaluation in production
    """
    
    # Get the best-performing prompts from previous runs
    client = Client()
    
    # Deploy best prompt to production
    deployment_config = deploy_best_prompt()
    
    # Set up monitoring
    monitoring_config = monitor_production_performance(deployment_config)
    
    # Check if retraining is needed based on performance
    retraining_decision = trigger_retraining_if_needed(monitoring_config)
    
    logger.info("🏭 Production deployment pipeline demonstrates:")
    logger.info("• Automated deployment of validated prompts")
    logger.info("• Real-time performance monitoring")
    logger.info("• Quality degradation detection")
    logger.info("• Automated rollback capabilities")
    logger.info("• Continuous evaluation loops")