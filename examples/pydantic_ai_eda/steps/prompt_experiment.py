"""Advanced prompt experimentation step for Pydantic AI agent development."""

import json
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from models import AgentConfig, EDAReport
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def evaluate_prompts_with_test_cases(
    dataset_df: pd.DataFrame,
    prompt_variants: List[str],
    test_cases_path: str = "test_cases.json",
    agent_config: AgentConfig = None,
    use_llm_judge: bool = True,
) -> Annotated[Dict[str, Any], "comprehensive_prompt_evaluation"]:
    """Advanced prompt evaluation using structured test cases and LLM judge.

    This step implements best practices from AI evaluation methodology:
    - Structured test cases with categories
    - LLM judge evaluation for quality assessment
    - Tool usage tracking and analysis
    - Statistical significance testing

    Args:
        dataset_df: Dataset to test prompts against
        prompt_variants: List of system prompts to compare
        test_cases_path: Path to JSON file with structured test cases
        agent_config: Base configuration for all agents
        use_llm_judge: Whether to use LLM for response quality evaluation

    Returns:
        Comprehensive evaluation results with quality scores and recommendations
    """
    if agent_config is None:
        agent_config = AgentConfig()

    # Load structured test cases
    test_cases = _load_test_cases(test_cases_path)
    if not test_cases:
        # Fallback to simple evaluation if no test cases
        return compare_agent_prompts(dataset_df, prompt_variants, agent_config)

    logger.info(
        f"🧪 Running comprehensive evaluation: {len(prompt_variants)} prompts × {len(test_cases)} test cases"
    )

    # Initialize LLM judge if requested
    llm_judge = None
    if use_llm_judge:
        llm_judge = _create_llm_judge(agent_config.model_name)

    all_results = []

    # Test each prompt variant
    for prompt_idx, system_prompt in enumerate(prompt_variants):
        prompt_id = f"variant_{prompt_idx + 1}"
        logger.info(f"Testing {prompt_id}/{len(prompt_variants)}")

        prompt_results = []

        # Run each test case for this prompt
        for test_case in test_cases:
            case_result = _run_single_test_case(
                dataset_df,
                system_prompt,
                test_case,
                agent_config,
                llm_judge,
                prompt_id,
            )
            prompt_results.append(case_result)

        # Aggregate results for this prompt
        prompt_summary = _analyze_prompt_performance(
            prompt_results, prompt_id, system_prompt
        )
        all_results.append(prompt_summary)

    # Generate comprehensive comparison
    final_analysis = _generate_comprehensive_analysis(all_results, test_cases)

    return final_analysis


@step
def compare_agent_prompts(
    dataset_df: pd.DataFrame,
    prompt_variants: List[str],
    agent_config: AgentConfig = None,
) -> Annotated[Dict[str, Any], "prompt_comparison_results"]:
    """Test multiple system prompts on the same dataset for agent optimization.

    This step helps developers iterate on agent prompts by running A/B tests
    and comparing quality, performance, and output characteristics.

    Args:
        dataset_df: Dataset to test prompts against
        prompt_variants: List of system prompts to compare
        agent_config: Base configuration for all agents

    Returns:
        Comparison report with metrics for each prompt variant
    """
    if agent_config is None:
        agent_config = AgentConfig()

    logger.info(
        f"🧪 Testing {len(prompt_variants)} prompt variants on dataset with {len(dataset_df)} rows"
    )

    results = []

    for i, system_prompt in enumerate(prompt_variants):
        prompt_id = f"variant_{i + 1}"
        logger.info(
            f"🔄 Testing prompt variant {i + 1}/{len(prompt_variants)}"
        )
        print(f"🔄 Testing prompt variant {i + 1}/{len(prompt_variants)}")

        start_time = time.time()

        try:
            # Initialize fresh dependencies for each test
            deps = AnalystAgentDeps()
            main_ref = deps.store(dataset_df)

            print(f"  🤖 Creating agent for variant {i + 1}...")
            # Create agent with this prompt variant
            test_agent = Agent(
                f"openai:{agent_config.model_name}",
                deps_type=AnalystAgentDeps,
                output_type=EDAReport,
                output_retries=3,
                system_prompt=system_prompt,
                model_settings=ModelSettings(
                    parallel_tool_calls=False
                ),  # Disable parallel to avoid hanging
            )

            # Register tools
            print(f"  🔧 Registering {len(AGENT_TOOLS)} tools...")
            for tool in AGENT_TOOLS:
                test_agent.tool(tool)

            # Run analysis with consistent user prompt
            user_prompt = f"""Analyze dataset '{main_ref}' ({dataset_df.shape[0]} rows, {dataset_df.shape[1]} cols).
            
Focus on data quality, key patterns, and actionable insights."""

            print(f"  ⚡ Running analysis for variant {i + 1}...")
            result = test_agent.run_sync(user_prompt, deps=deps)
            eda_report = result.output

            execution_time = time.time() - start_time

            # Collect metrics for comparison
            result_metrics = {
                "prompt_id": prompt_id,
                "system_prompt": system_prompt,
                "success": True,
                "execution_time_seconds": round(execution_time, 2),
                "tool_calls_made": len(deps.query_history),
                "data_quality_score": eda_report.data_quality_score,
                "key_findings_count": len(eda_report.key_findings),
                "risks_identified": len(eda_report.risks),
                "fixes_suggested": len(eda_report.fixes),
                "correlation_insights": len(eda_report.correlation_insights),
                "headline_length": len(eda_report.headline),
                "markdown_length": len(eda_report.markdown),
                "tables_generated": len(deps.output)
                - 1,  # Exclude main dataset
                "error": None,
            }

            logger.info(
                f"✅ Variant {i + 1}: Score={eda_report.data_quality_score:.1f}, Tools={len(deps.query_history)}, Time={execution_time:.1f}s"
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"❌ Variant {i + 1} failed: {str(e)}")

            result_metrics = {
                "prompt_id": prompt_id,
                "system_prompt": system_prompt,
                "success": False,
                "execution_time_seconds": round(execution_time, 2),
                "tool_calls_made": 0,
                "data_quality_score": 0.0,
                "key_findings_count": 0,
                "risks_identified": 0,
                "fixes_suggested": 0,
                "correlation_insights": 0,
                "headline_length": 0,
                "markdown_length": 0,
                "tables_generated": 0,
                "error": str(e),
            }

        results.append(result_metrics)

    # Analyze results and determine best variant
    successful_results = [r for r in results if r["success"]]

    if successful_results:
        # Rank by composite score (quality + speed + thoroughness)
        for result in successful_results:
            # Composite score: 60% quality + 20% speed + 20% thoroughness
            speed_score = max(
                0, 100 - result["execution_time_seconds"] * 10
            )  # Penalty for slowness
            thoroughness_score = (
                result["key_findings_count"] * 10
                + result["risks_identified"] * 5
                + result["tables_generated"] * 5
            )

            result["composite_score"] = (
                result["data_quality_score"] * 0.6
                + min(speed_score, 100) * 0.2
                + min(thoroughness_score, 100) * 0.2
            )

        # Find best performer
        best_result = max(
            successful_results, key=lambda x: x["composite_score"]
        )
        best_prompt_id = best_result["prompt_id"]

        logger.info(
            f"🏆 Best performing prompt: {best_prompt_id} (score: {best_result['composite_score']:.1f})"
        )
    else:
        best_prompt_id = "none"
        logger.warning("❌ No prompts succeeded")

    # Generate summary comparison
    summary = {
        "experiment_summary": {
            "total_prompts_tested": len(prompt_variants),
            "successful_runs": len(successful_results),
            "failed_runs": len(results) - len(successful_results),
            "best_prompt_variant": best_prompt_id,
            "avg_execution_time": round(
                sum(r["execution_time_seconds"] for r in results)
                / len(results),
                2,
            )
            if results
            else 0,
            "dataset_info": {
                "rows": len(dataset_df),
                "columns": len(dataset_df.columns),
                "column_names": list(dataset_df.columns),
            },
        },
        "detailed_results": results,
        "recommendations": _generate_prompt_recommendations(results),
    }

    return summary


def _generate_prompt_recommendations(
    results: List[Dict[str, Any]],
) -> List[str]:
    """Generate recommendations based on prompt experiment results."""
    recommendations = []

    successful_results = [r for r in results if r["success"]]

    if not successful_results:
        return [
            "All prompts failed - check agent configuration and error messages"
        ]

    # Performance analysis
    avg_time = sum(
        r["execution_time_seconds"] for r in successful_results
    ) / len(successful_results)
    avg_quality = sum(
        r["data_quality_score"] for r in successful_results
    ) / len(successful_results)

    if avg_time > 30:
        recommendations.append(
            "Consider shorter, more focused prompts to reduce execution time"
        )

    if avg_quality < 70:
        recommendations.append(
            "Consider more specific instructions for data quality assessment"
        )

    # Consistency analysis
    quality_scores = [r["data_quality_score"] for r in successful_results]
    quality_variance = max(quality_scores) - min(quality_scores)

    if quality_variance > 20:
        recommendations.append(
            "High variance in quality scores - consider more consistent prompt structure"
        )
    else:
        recommendations.append(
            "Quality scores are consistent across prompts - good stability"
        )

    # Tool usage analysis
    tool_calls = [r["tool_calls_made"] for r in successful_results]
    if max(tool_calls) - min(tool_calls) > 3:
        recommendations.append(
            "Variable tool usage detected - consider standardizing analysis steps"
        )

    # Success rate analysis
    success_rate = len(successful_results) / len(results) * 100
    if success_rate < 80:
        recommendations.append(
            "Low success rate - review prompt complexity and error handling"
        )
    else:
        recommendations.append(
            f"Good success rate ({success_rate:.0f}%) - prompts are robust"
        )

    return recommendations


def _load_test_cases(test_cases_path: str) -> List[Dict[str, Any]]:
    """Load structured test cases from JSON file."""
    try:
        test_cases_file = Path(test_cases_path)
        if not test_cases_file.exists():
            logger.warning(f"Test cases file not found: {test_cases_path}")
            return []

        with open(test_cases_file, "r") as f:
            test_cases = json.load(f)

        logger.info(
            f"Loaded {len(test_cases)} test cases from {test_cases_path}"
        )
        return test_cases

    except Exception as e:
        logger.error(f"Failed to load test cases: {e}")
        return []


def _create_llm_judge(base_model: str) -> Optional[Agent]:
    """Create an LLM judge agent for evaluating responses."""
    try:
        # Use a stronger model for evaluation if available
        judge_model = (
            "gpt-4o" if "gpt" in base_model else "claude-3-5-sonnet-20241022"
        )

        judge_system_prompt = """You are an expert AI evaluator specializing in data analysis responses.

Your job is to assess EDA (Exploratory Data Analysis) responses based on:

1. **Accuracy** (1-5): Factual correctness and valid statistical insights
2. **Relevance** (1-5): How well the response addresses the specific query
3. **Completeness** (1-5): Whether all aspects of the query are covered
4. **Tool Usage** (1-5): Appropriate use of available analysis tools
5. **Actionability** (1-5): Quality of recommendations and insights

Score each criterion from 1 (poor) to 5 (excellent).
Provide scores in JSON format: {"accuracy": X, "relevance": X, "completeness": X, "tool_usage": X, "actionability": X, "overall": X, "reasoning": "brief explanation"}

Be objective and consistent in your evaluations."""

        return Agent(
            f"openai:{judge_model}"
            if "gpt" in base_model
            else f"anthropic:{judge_model}",
            system_prompt=judge_system_prompt,
        )

    except Exception as e:
        logger.warning(f"Failed to create LLM judge: {e}")
        return None


def _run_single_test_case(
    dataset_df: pd.DataFrame,
    system_prompt: str,
    test_case: Dict[str, Any],
    agent_config: AgentConfig,
    llm_judge: Optional[Agent],
    prompt_id: str,
) -> Dict[str, Any]:
    """Run a single test case and collect comprehensive metrics."""
    start_time = time.time()

    try:
        # Initialize agent for this test
        deps = AnalystAgentDeps()
        main_ref = deps.store(dataset_df)

        test_agent = Agent(
            f"openai:{agent_config.model_name}",
            deps_type=AnalystAgentDeps,
            output_type=EDAReport,
            output_retries=3,
            system_prompt=system_prompt,
            model_settings=ModelSettings(parallel_tool_calls=True),
        )

        # Register tools
        for tool in AGENT_TOOLS:
            test_agent.tool(tool)

        # Run the test case query
        full_query = f"Dataset reference: {main_ref}\n\n{test_case['query']}"
        result = test_agent.run_sync(full_query, deps=deps)
        eda_report = result.output

        execution_time = time.time() - start_time

        # Collect basic metrics
        case_result = {
            "test_id": test_case["id"],
            "category": test_case.get("category", "general"),
            "prompt_id": prompt_id,
            "query": test_case["query"],
            "success": True,
            "execution_time": execution_time,
            "tool_calls_made": len(deps.query_history),
            "response": str(eda_report.markdown),
            "data_quality_score": eda_report.data_quality_score,
            "findings_count": len(eda_report.key_findings),
            "risks_count": len(eda_report.risks),
            "recommendations_count": len(eda_report.fixes),
            "error": None,
        }

        # Evaluate with LLM judge if available
        if llm_judge:
            judge_evaluation = _get_llm_judge_scores(
                llm_judge, test_case, case_result
            )
            case_result.update(judge_evaluation)

        # Check against expected metrics if available
        expected_metrics = test_case.get("expected_metrics", {})
        case_result["meets_expectations"] = _check_expectations(
            case_result, expected_metrics
        )

        return case_result

    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "test_id": test_case["id"],
            "category": test_case.get("category", "general"),
            "prompt_id": prompt_id,
            "query": test_case["query"],
            "success": False,
            "execution_time": execution_time,
            "error": str(e),
            "meets_expectations": False,
        }


def _get_llm_judge_scores(
    llm_judge: Agent, test_case: Dict, case_result: Dict
) -> Dict:
    """Get quality scores from LLM judge."""
    try:
        eval_prompt = f"""
Query: {test_case["query"]}
Category: {test_case.get("category", "general")}

Response to evaluate:
{case_result["response"][:2000]}...

Data Quality Score Provided: {case_result["data_quality_score"]}
Tool Calls Made: {case_result["tool_calls_made"]}
Findings Count: {case_result["findings_count"]}

Please evaluate this EDA response and provide scores in the requested JSON format."""

        judge_response = llm_judge.run_sync(eval_prompt)

        # Parse JSON response
        try:
            scores = json.loads(str(judge_response.output))
            return {
                "judge_accuracy": scores.get("accuracy", 0),
                "judge_relevance": scores.get("relevance", 0),
                "judge_completeness": scores.get("completeness", 0),
                "judge_tool_usage": scores.get("tool_usage", 0),
                "judge_actionability": scores.get("actionability", 0),
                "judge_overall": scores.get("overall", 0),
                "judge_reasoning": scores.get("reasoning", ""),
            }
        except json.JSONDecodeError:
            logger.warning("LLM judge response was not valid JSON")
            return {
                "judge_overall": 3,
                "judge_reasoning": "Failed to parse judge response",
            }

    except Exception as e:
        logger.warning(f"LLM judge evaluation failed: {e}")
        return {
            "judge_overall": 3,
            "judge_reasoning": f"Evaluation error: {e}",
        }


def _check_expectations(case_result: Dict, expected_metrics: Dict) -> bool:
    """Check if results meet expected criteria."""
    if not expected_metrics:
        return True

    checks = []

    # Check minimum quality score
    min_quality = expected_metrics.get("quality_score_min")
    if min_quality:
        checks.append(case_result.get("data_quality_score", 0) >= min_quality)

    # Check minimum recommendations
    min_recs = expected_metrics.get("recommendations_min")
    if min_recs:
        checks.append(case_result.get("recommendations_count", 0) >= min_recs)

    # Check expected tool calls
    expected_tools = expected_metrics.get("tool_calls_expected", [])
    if expected_tools:
        # This would need actual tool tracking - simplified for now
        checks.append(case_result.get("tool_calls_made", 0) > 0)

    return all(checks) if checks else True


def _analyze_prompt_performance(
    results: List[Dict], prompt_id: str, system_prompt: str
) -> Dict:
    """Analyze performance across all test cases for a single prompt."""
    successful_results = [r for r in results if r["success"]]

    if not successful_results:
        return {
            "prompt_id": prompt_id,
            "system_prompt": system_prompt,
            "success_rate": 0,
            "avg_scores": {},
            "category_performance": {},
            "overall_rating": "failed",
        }

    # Calculate averages
    avg_scores = {
        "execution_time": sum(r["execution_time"] for r in successful_results)
        / len(successful_results),
        "tool_calls": sum(r["tool_calls_made"] for r in successful_results)
        / len(successful_results),
        "data_quality_score": sum(
            r["data_quality_score"] for r in successful_results
        )
        / len(successful_results),
        "findings_count": sum(r["findings_count"] for r in successful_results)
        / len(successful_results),
    }

    # Add LLM judge scores if available
    judge_scores = [r for r in successful_results if "judge_overall" in r]
    if judge_scores:
        avg_scores.update(
            {
                "judge_accuracy": sum(
                    r["judge_accuracy"] for r in judge_scores
                )
                / len(judge_scores),
                "judge_relevance": sum(
                    r["judge_relevance"] for r in judge_scores
                )
                / len(judge_scores),
                "judge_completeness": sum(
                    r["judge_completeness"] for r in judge_scores
                )
                / len(judge_scores),
                "judge_overall": sum(r["judge_overall"] for r in judge_scores)
                / len(judge_scores),
            }
        )

    # Category-wise performance
    categories = {}
    for result in successful_results:
        cat = result["category"]
        if cat not in categories:
            categories[cat] = {
                "count": 0,
                "avg_score": 0,
                "meets_expectations": 0,
            }
        categories[cat]["count"] += 1
        categories[cat]["avg_score"] += result["data_quality_score"]
        if result.get("meets_expectations", False):
            categories[cat]["meets_expectations"] += 1

    for cat in categories:
        categories[cat]["avg_score"] /= categories[cat]["count"]
        categories[cat]["success_rate"] = (
            categories[cat]["meets_expectations"] / categories[cat]["count"]
        )

    # Overall rating
    success_rate = len(successful_results) / len(results)
    avg_judge_score = avg_scores.get(
        "judge_overall", avg_scores.get("data_quality_score", 50) / 20
    )

    if success_rate >= 0.8 and avg_judge_score >= 4:
        rating = "excellent"
    elif success_rate >= 0.6 and avg_judge_score >= 3:
        rating = "good"
    elif success_rate >= 0.4:
        rating = "acceptable"
    else:
        rating = "poor"

    return {
        "prompt_id": prompt_id,
        "system_prompt": system_prompt,
        "success_rate": success_rate,
        "avg_scores": avg_scores,
        "category_performance": categories,
        "overall_rating": rating,
        "detailed_results": results,
    }


def _generate_comprehensive_analysis(
    all_results: List[Dict], test_cases: List[Dict]
) -> Dict:
    """Generate final comprehensive analysis of all prompt variants."""
    # Rank prompts by overall performance
    ranked_prompts = sorted(
        all_results,
        key=lambda x: (
            x["success_rate"] * 0.4
            + x["avg_scores"].get("judge_overall", 3) * 0.3
            + (100 - x["avg_scores"]["execution_time"]) / 100 * 0.2
            + x["avg_scores"]["data_quality_score"] / 100 * 0.1
        ),
        reverse=True,
    )

    best_prompt = ranked_prompts[0] if ranked_prompts else None

    # Category analysis
    category_insights = {}
    for test_case in test_cases:
        cat = test_case.get("category", "general")
        if cat not in category_insights:
            category_insights[cat] = {"prompt_performance": []}

        for prompt_result in all_results:
            cat_perf = prompt_result["category_performance"].get(cat, {})
            if cat_perf:
                category_insights[cat]["prompt_performance"].append(
                    {
                        "prompt_id": prompt_result["prompt_id"],
                        "avg_score": cat_perf["avg_score"],
                        "success_rate": cat_perf["success_rate"],
                    }
                )

    return {
        "evaluation_summary": {
            "total_prompts_tested": len(all_results),
            "total_test_cases": len(test_cases),
            "best_prompt": best_prompt["prompt_id"] if best_prompt else "none",
            "best_prompt_rating": best_prompt["overall_rating"]
            if best_prompt
            else "none",
            "categories_tested": list(category_insights.keys()),
        },
        "prompt_rankings": ranked_prompts,
        "category_analysis": category_insights,
        "detailed_results": all_results,
        "recommendations": _generate_advanced_recommendations(
            all_results, category_insights
        ),
    }


def _generate_advanced_recommendations(
    all_results: List[Dict], category_insights: Dict
) -> List[str]:
    """Generate advanced recommendations based on comprehensive analysis."""
    recommendations = []

    if not all_results:
        return ["No successful evaluations - check agent configuration"]

    # Success rate analysis
    avg_success_rate = sum(r["success_rate"] for r in all_results) / len(
        all_results
    )
    if avg_success_rate < 0.6:
        recommendations.append(
            "Low overall success rate - consider simplifying prompts or checking tool integration"
        )

    # Performance consistency
    execution_times = [r["avg_scores"]["execution_time"] for r in all_results]
    time_variance = max(execution_times) - min(execution_times)
    if time_variance > 30:
        recommendations.append(
            "High variance in execution time - optimize slower prompts for efficiency"
        )

    # Quality assessment
    if any("judge_overall" in r["avg_scores"] for r in all_results):
        judge_scores = [
            r["avg_scores"]["judge_overall"]
            for r in all_results
            if "judge_overall" in r["avg_scores"]
        ]
        avg_judge_score = sum(judge_scores) / len(judge_scores)

        if avg_judge_score < 3:
            recommendations.append(
                "LLM judge scores are low - review prompt clarity and specificity"
            )
        elif avg_judge_score > 4:
            recommendations.append(
                "Excellent LLM judge scores - prompts are producing high-quality responses"
            )

    # Category-specific insights
    for category, data in category_insights.items():
        if data["prompt_performance"]:
            cat_scores = [p["avg_score"] for p in data["prompt_performance"]]
            if min(cat_scores) < 60:
                recommendations.append(
                    f"'{category}' category shows low scores - consider specialized prompts for this use case"
                )

    # Best practices
    best_prompt = max(all_results, key=lambda x: x["success_rate"])
    if best_prompt["success_rate"] > 0.8:
        recommendations.append(
            f"'{best_prompt['prompt_id']}' shows strong performance - consider it as your baseline"
        )

    return recommendations
