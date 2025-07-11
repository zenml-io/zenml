"""Evaluation steps for the agent comparison pipeline."""

from typing import Dict, List

import numpy as np
import pandas as pd
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def evaluate_and_decide(
    queries: pd.DataFrame, results: Dict[str, Dict[str, List[float]]]
) -> Annotated[HTMLString, "architecture_comparison_report"]:
    """Evaluate results and generate a recommendation report.

    Args:
        queries: DataFrame containing the test queries used for evaluation
        results: Dictionary of architecture performance metrics

    Returns:
        HTML string containing comprehensive comparison report with recommendations
    """
    evaluation_data = []

    for arch_name, response_data in results.items():
        # Calculate metrics for each architecture
        latencies = response_data["latencies"]
        confidences = response_data["confidences"]
        tokens = response_data["tokens_used"]

        metrics = {
            "architecture": arch_name,
            "avg_latency_ms": np.mean(latencies),
            "p95_latency_ms": np.percentile(latencies, 95),
            "avg_confidence": np.mean(confidences),
            "avg_tokens_used": np.mean(tokens),
            "total_cost_estimate": np.sum(tokens)
            * 0.0001,  # Mock cost calculation
            "response_quality": np.mean(confidences)
            * 100,  # Simplified quality score
        }

        # Calculate overall score (lower is better for latency/cost, higher for quality/confidence)
        overall_score = (
            metrics["avg_confidence"] * 0.4
            + (1 - metrics["avg_latency_ms"] / 1000) * 0.3
            + (1 - metrics["total_cost_estimate"] / 10) * 0.3
        )
        metrics["overall_score"] = overall_score

        evaluation_data.append(metrics)

    # Create evaluation DataFrame
    evaluation_df = pd.DataFrame(evaluation_data)

    # Find the winner
    winner = evaluation_df.loc[evaluation_df["overall_score"].idxmax()]

    # Generate comprehensive HTML report
    report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Agent Architecture Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 8px; }}
        .winner {{ background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .architecture {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .workflow {{ background-color: #e1f5fe; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 5px 10px; padding: 5px 10px; background-color: #fff; border-radius: 3px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        h3 {{ color: #888; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Agent Architecture Comparison Report</h1>
        <h2>Executive Summary</h2>
        <p>After testing {len(evaluation_df)} different agent architectures on {len(queries)} customer service queries,
        the <strong>{winner["architecture"]}</strong> architecture performed best with an overall score of {winner["overall_score"]:.3f}.</p>
    </div>

    <div class="winner">
        <h2>🏆 Winner: {winner["architecture"]}</h2>
        <div class="metric">Avg Latency: {winner["avg_latency_ms"]:.1f}ms</div>
        <div class="metric">Confidence: {winner["avg_confidence"]:.3f}</div>
        <div class="metric">Quality: {winner["response_quality"]:.1f}/100</div>
        <div class="metric">Cost: ${winner["total_cost_estimate"]:.4f}</div>
    </div>

    <div class="workflow">
        <h2>🔄 LangGraph Workflow Architecture</h2>
        <p>The LangGraph agent uses a structured workflow:</p>
        <p><strong>START → analyze_query → classify_intent → generate_response → validate_response → END</strong></p>
        <h3>Node Details:</h3>
        <ul>
            <li><strong>analyze_query:</strong> Analyzes query complexity and sets initial confidence</li>
            <li><strong>classify_intent:</strong> Classifies into returns, billing, shipping, warranty, or general</li>
            <li><strong>generate_response:</strong> Generates appropriate response based on intent</li>
            <li><strong>validate_response:</strong> Validates response quality and adjusts confidence</li>
        </ul>
        <p><em>📊 Interactive Mermaid Diagram available as separate artifact</em></p>
    </div>

    <h2>📊 Detailed Results</h2>
"""

    for _, row in evaluation_df.iterrows():
        report += f"""
    <div class="architecture">
        <h3>🔧 {row["architecture"]}</h3>
        <div class="metric">Overall Score: {row["overall_score"]:.3f}</div>
        <div class="metric">Avg Latency: {row["avg_latency_ms"]:.1f}ms</div>
        <div class="metric">P95 Latency: {row["p95_latency_ms"]:.1f}ms</div>
        <div class="metric">Confidence: {row["avg_confidence"]:.3f}</div>
        <div class="metric">Quality: {row["response_quality"]:.1f}/100</div>
        <div class="metric">Cost: ${row["total_cost_estimate"]:.4f}</div>
        <div class="metric">Tokens: {row["avg_tokens_used"]:.0f} avg</div>
    </div>
"""

    # Prepare advantage texts
    latency_advantage = (
        "Lowest latency"
        if winner["avg_latency_ms"] == evaluation_df["avg_latency_ms"].min()
        else "Good latency performance"
    )
    confidence_advantage = (
        "Highest confidence"
        if winner["avg_confidence"] == evaluation_df["avg_confidence"].max()
        else "Strong confidence scores"
    )
    cost_advantage = (
        "Most cost-effective"
        if winner["total_cost_estimate"]
        == evaluation_df["total_cost_estimate"].min()
        else "Reasonable cost structure"
    )

    report += f"""
    <div class="header">
        <h2>🚀 Recommendation</h2>
        <p><strong>Deploy {winner["architecture"]}</strong> to staging environment for further testing.</p>

        <h3>Key Advantages:</h3>
        <ul>
            <li>Highest overall performance score</li>
            <li>{latency_advantage}</li>
            <li>{confidence_advantage}</li>
            <li>{cost_advantage}</li>
        </ul>

        <h3>Next Steps:</h3>
        <ol>
            <li>Deploy {winner["architecture"]} to staging environment</li>
            <li>Run A/B test against current production system</li>
            <li>Monitor real-world performance metrics</li>
            <li>Collect customer satisfaction feedback</li>
        </ol>
    </div>

    <footer style="margin-top: 30px; padding: 20px; background-color: #f4f4f4; border-radius: 8px; text-align: center;">
        <p><em>Report generated by ZenML Agent Comparison Pipeline</em></p>
    </footer>
</body>
</html>
"""

    logger.info(f"Evaluation complete. Winner: {winner['architecture']}")
    return HTMLString(report)
