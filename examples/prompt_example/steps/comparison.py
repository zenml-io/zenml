"""Steps for comparing prompt variants and analyzing results."""

from datetime import datetime
from typing import Annotated, Any, Dict, List

from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.logger import get_logger
from zenml.types import Prompt

logger = get_logger(__name__)


@step
def compare_prompt_variants(
    variants: List[Prompt],
    responses: List[str],
    evaluations: List[Dict[str, float]],
) -> Annotated[
    Dict[str, Any],
    ArtifactConfig(name="prompt_comparison", tags=["comparison", "analysis"]),
]:
    """Compare multiple prompt variants and their performance."""

    comparison_results = {
        "comparison_timestamp": datetime.now().isoformat(),
        "total_variants": len(variants),
        "variants": {},
        "summary": {},
        "rankings": {},
        "insights": [],
    }

    # Analyze each variant
    for i, (variant, response, evaluation) in enumerate(
        zip(variants, responses, evaluations)
    ):
        variant_name = f"variant_{i + 1}_{variant.version or 'unknown'}"

        comparison_results["variants"][variant_name] = {
            "prompt_config": {
                "version": variant.version,
                "task": variant.task,
                "domain": variant.domain,
                "strategy": variant.prompt_strategy,
                "description": variant.description,
                "tags": variant.tags or [],
                "temperature": variant.model_config_params.get("temperature")
                if variant.model_config_params
                else None,
                "max_tokens": variant.model_config_params.get("max_tokens")
                if variant.model_config_params
                else None,
            },
            "template_analysis": {
                "template_length": len(variant.template),
                "variable_count": len(variant.variables or {}),
                "has_examples": bool(variant.examples),
                "has_instructions": bool(variant.instructions),
            },
            "response_analysis": {
                "response_length": len(response),
                "response_preview": response[:200] + "..."
                if len(response) > 200
                else response,
            },
            "performance_metrics": evaluation,
            "ranking": evaluation.get("rank", 0),
        }

    # Generate summary statistics
    comparison_results["summary"] = generate_summary_statistics(evaluations)

    # Create rankings
    comparison_results["rankings"] = create_performance_rankings(
        variants, evaluations
    )

    # Generate insights
    comparison_results["insights"] = generate_comparison_insights(
        variants, evaluations
    )

    # Identify best variant
    best_idx = max(
        range(len(evaluations)),
        key=lambda i: evaluations[i]["overall_quality"],
    )
    comparison_results["best_variant"] = {
        "index": best_idx,
        "name": f"variant_{best_idx + 1}_{variants[best_idx].version or 'unknown'}",
        "score": evaluations[best_idx]["overall_quality"],
        "description": variants[best_idx].description,
    }

    logger.info(
        f"Comparison completed. Best variant: {comparison_results['best_variant']['name']}"
    )
    return comparison_results


@step
def analyze_best_prompt(
    comparison: Dict[str, Any],
) -> Annotated[
    Dict[str, Any],
    ArtifactConfig(
        name="best_prompt_analysis", tags=["analysis", "optimization"]
    ),
]:
    """Analyze the best performing prompt for insights and recommendations."""

    best_variant_name = comparison["best_variant"]["name"]
    best_variant_data = comparison["variants"][best_variant_name]

    analysis = {
        "analysis_timestamp": datetime.now().isoformat(),
        "best_variant": best_variant_name,
        "performance_summary": {
            "overall_quality": comparison["best_variant"]["score"],
            "ranking": 1,
            "percentile": 100,
        },
        "success_factors": [],
        "optimization_opportunities": [],
        "recommended_variations": [],
        "deployment_readiness": {},
    }

    # Analyze what made this prompt successful
    config = best_variant_data["prompt_config"]
    metrics = best_variant_data["performance_metrics"]

    # Identify success factors
    if metrics.get("overall_quality", 0) > 0.8:
        analysis["success_factors"].append("High overall quality score")

    if metrics.get("completeness_score", 0) > 0.8:
        analysis["success_factors"].append(
            "Complete and comprehensive responses"
        )

    if metrics.get("relevance_score", 0) > 0.8:
        analysis["success_factors"].append("Highly relevant to the task")

    if metrics.get("clarity_score", 0) > 0.8:
        analysis["success_factors"].append("Clear and well-structured output")

    if config.get("strategy") == "structured":
        analysis["success_factors"].append(
            "Effective use of structured prompting"
        )

    # Identify optimization opportunities
    if metrics.get("format_compliance", 1) < 0.9:
        analysis["optimization_opportunities"].append(
            "Improve format compliance"
        )

    if metrics.get("token_efficiency", 0.5) < 0.7:
        analysis["optimization_opportunities"].append(
            "Optimize token usage efficiency"
        )

    if not best_variant_data["template_analysis"]["has_examples"]:
        analysis["optimization_opportunities"].append(
            "Consider adding examples for better guidance"
        )

    # Generate recommended variations
    analysis["recommended_variations"] = generate_prompt_variations(
        config, metrics
    )

    # Assess deployment readiness
    analysis["deployment_readiness"] = assess_deployment_readiness(
        config, metrics
    )

    logger.info(
        f"Best prompt analysis completed with {len(analysis['success_factors'])} success factors"
    )
    return analysis


def generate_summary_statistics(
    evaluations: List[Dict[str, float]],
) -> Dict[str, float]:
    """Generate summary statistics across all evaluations."""

    if not evaluations:
        return {}

    # Collect all metric names
    all_metrics = set()
    for evaluation in evaluations:
        all_metrics.update(evaluation.keys())

    summary = {}

    for metric in all_metrics:
        values = [eval.get(metric, 0) for eval in evaluations]
        summary[f"{metric}_mean"] = sum(values) / len(values)
        summary[f"{metric}_max"] = max(values)
        summary[f"{metric}_min"] = min(values)
        summary[f"{metric}_std"] = calculate_std(values)

    return summary


def create_performance_rankings(
    variants: List[Prompt], evaluations: List[Dict[str, float]]
) -> Dict[str, List[Dict]]:
    """Create performance rankings across different metrics."""

    rankings = {
        "overall_quality": [],
        "completeness": [],
        "relevance": [],
        "clarity": [],
    }

    for metric_key, ranking_list in rankings.items():
        # Map metric names
        eval_key = {
            "overall_quality": "overall_quality",
            "completeness": "completeness_score",
            "relevance": "relevance_score",
            "clarity": "clarity_score",
        }[metric_key]

        # Create ranking
        indexed_scores = [
            (i, eval.get(eval_key, 0)) for i, eval in enumerate(evaluations)
        ]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (variant_idx, score) in enumerate(indexed_scores, 1):
            ranking_list.append(
                {
                    "rank": rank,
                    "variant_index": variant_idx,
                    "variant_name": f"variant_{variant_idx + 1}_{variants[variant_idx].version or 'unknown'}",
                    "score": score,
                    "strategy": variants[variant_idx].prompt_strategy,
                    "domain": variants[variant_idx].domain,
                }
            )

    return rankings


def generate_comparison_insights(
    variants: List[Prompt], evaluations: List[Dict[str, float]]
) -> List[str]:
    """Generate insights from the comparison analysis."""

    insights = []

    # Strategy effectiveness insights
    strategy_scores = {}
    for variant, evaluation in zip(variants, evaluations):
        strategy = variant.prompt_strategy or "unknown"
        if strategy not in strategy_scores:
            strategy_scores[strategy] = []
        strategy_scores[strategy].append(evaluation.get("overall_quality", 0))

    for strategy, scores in strategy_scores.items():
        if len(scores) > 0:
            avg_score = sum(scores) / len(scores)
            insights.append(
                f"Strategy '{strategy}' achieved average quality score of {avg_score:.2f}"
            )

    # Temperature analysis
    temp_analysis = {}
    for variant, evaluation in zip(variants, evaluations):
        if (
            variant.model_config_params
            and "temperature" in variant.model_config_params
        ):
            temp = variant.model_config_params["temperature"]
            temp_range = (
                "low" if temp <= 0.3 else "medium" if temp <= 0.6 else "high"
            )
            if temp_range not in temp_analysis:
                temp_analysis[temp_range] = []
            temp_analysis[temp_range].append(
                evaluation.get("overall_quality", 0)
            )

    for temp_range, scores in temp_analysis.items():
        if len(scores) > 0:
            avg_score = sum(scores) / len(scores)
            insights.append(
                f"{temp_range.capitalize()} temperature settings achieved average quality of {avg_score:.2f}"
            )

    # Domain effectiveness
    domain_scores = {}
    for variant, evaluation in zip(variants, evaluations):
        domain = variant.domain or "general"
        if domain not in domain_scores:
            domain_scores[domain] = []
        domain_scores[domain].append(evaluation.get("overall_quality", 0))

    best_domain = max(
        domain_scores.keys(),
        key=lambda d: sum(domain_scores[d]) / len(domain_scores[d]),
    )
    best_domain_score = sum(domain_scores[best_domain]) / len(
        domain_scores[best_domain]
    )
    insights.append(
        f"Domain '{best_domain}' performed best with average score of {best_domain_score:.2f}"
    )

    # Response length insights
    lengths = [eval.get("response_length", 0) for eval in evaluations]
    qualities = [eval.get("overall_quality", 0) for eval in evaluations]

    if len(lengths) > 1:
        # Simple correlation analysis
        avg_length = sum(lengths) / len(lengths)
        long_responses = [
            qualities[i]
            for i, length in enumerate(lengths)
            if length > avg_length
        ]
        short_responses = [
            qualities[i]
            for i, length in enumerate(lengths)
            if length <= avg_length
        ]

        if long_responses and short_responses:
            long_avg = sum(long_responses) / len(long_responses)
            short_avg = sum(short_responses) / len(short_responses)

            if long_avg > short_avg:
                insights.append(
                    "Longer responses tend to have higher quality scores"
                )
            else:
                insights.append(
                    "Concise responses perform as well as longer ones"
                )

    return insights


def generate_prompt_variations(
    config: Dict, metrics: Dict[str, float]
) -> List[Dict[str, str]]:
    """Generate recommended prompt variations based on performance analysis."""

    variations = []

    # Temperature optimization
    current_temp = config.get("temperature", 0.5)
    if metrics.get("clarity_score", 0) < 0.8:
        new_temp = max(0.1, current_temp - 0.2)
        variations.append(
            {
                "type": "temperature_adjustment",
                "recommendation": f"Lower temperature to {new_temp} for clearer responses",
                "rationale": "Current clarity score suggests more focused output needed",
            }
        )

    # Strategy optimization
    current_strategy = config.get("strategy", "direct")
    if metrics.get("completeness_score", 0) < 0.8:
        if current_strategy != "structured":
            variations.append(
                {
                    "type": "strategy_change",
                    "recommendation": "Switch to structured prompting strategy",
                    "rationale": "Structured approach may improve completeness",
                }
            )

    # Token optimization
    if metrics.get("token_efficiency", 0.5) < 0.6:
        variations.append(
            {
                "type": "token_optimization",
                "recommendation": "Reduce max_tokens or refine prompt template",
                "rationale": "Current token usage is inefficient",
            }
        )

    return variations


def assess_deployment_readiness(
    config: Dict, metrics: Dict[str, float]
) -> Dict[str, Any]:
    """Assess if the prompt is ready for production deployment."""

    readiness = {
        "score": 0,
        "status": "not_ready",
        "requirements_met": [],
        "requirements_missing": [],
        "recommendations": [],
    }

    # Quality thresholds
    quality_checks = {
        "overall_quality": 0.8,
        "completeness_score": 0.7,
        "relevance_score": 0.8,
        "clarity_score": 0.7,
    }

    passed_checks = 0
    for check, threshold in quality_checks.items():
        if metrics.get(check, 0) >= threshold:
            passed_checks += 1
            readiness["requirements_met"].append(f"{check} >= {threshold}")
        else:
            readiness["requirements_missing"].append(
                f"{check} < {threshold} (current: {metrics.get(check, 0):.2f})"
            )

    readiness["score"] = passed_checks / len(quality_checks)

    if readiness["score"] >= 0.8:
        readiness["status"] = "ready"
    elif readiness["score"] >= 0.6:
        readiness["status"] = "needs_improvement"
    else:
        readiness["status"] = "not_ready"

    # Add recommendations
    if readiness["score"] < 1.0:
        readiness["recommendations"] = [
            "Improve failing quality metrics",
            "Test with more diverse inputs",
            "Validate with domain experts",
        ]

    return readiness


def calculate_std(values: List[float]) -> float:
    """Calculate standard deviation of a list of values."""
    if len(values) <= 1:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance**0.5
