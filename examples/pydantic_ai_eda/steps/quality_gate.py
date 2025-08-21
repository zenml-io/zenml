"""Quality gate step for data quality assessment and pipeline routing."""

import logging
from typing import Annotated, Any, Dict, List, Tuple

from models import QualityGateDecision

from zenml import step

logger = logging.getLogger(__name__)


def _check_quality_metric(
    condition: bool,
    pass_msg: str,
    fail_msg: str,
    blocking_issues: List[str],
    decision_factors: List[str],
) -> None:
    """Helper to standardize quality check pattern."""
    if condition:
        blocking_issues.append(fail_msg)
        decision_factors.append(f"{pass_msg.split(':')[0]}: ❌")
    else:
        decision_factors.append(f"{pass_msg}: ✅")


def evaluate_quality_gate(
    report_json: Dict[str, Any],
    min_quality_score: float = 70.0,
    block_on_high_severity: bool = True,
    max_missing_data_pct: float = 30.0,
    require_target_column: bool = False,
    target_column: str = None,
) -> Annotated[QualityGateDecision, "quality_gate_decision"]:
    """Evaluate data quality and make gate pass/fail decision."""
    logger.info("Evaluating data quality gate")

    try:
        # Extract metrics
        quality_score = report_json.get("data_quality_score", 0.0)
        fixes = report_json.get("fixes", [])
        missing_data_analysis = report_json.get("missing_data_analysis", {})
        column_profiles = report_json.get("column_profiles", {})

        blocking_issues = []
        decision_factors = []

        # Quality score check
        _check_quality_metric(
            quality_score < min_quality_score,
            f"Quality score: {quality_score:.1f}/{min_quality_score}",
            f"Data quality score ({quality_score:.1f}) below minimum threshold ({min_quality_score})",
            blocking_issues,
            decision_factors,
        )

        # High severity issues check
        high_severity_fixes = [f for f in fixes if f.get("severity") == "high"]
        if block_on_high_severity and high_severity_fixes:
            titles = [f.get("title", "Unknown") for f in high_severity_fixes]
            _check_quality_metric(
                True,
                f"High severity issues: {len(high_severity_fixes)}",
                f"High severity issues found: {', '.join(titles)}",
                blocking_issues,
                decision_factors,
            )
        else:
            decision_factors.append(
                f"High severity issues: {len(high_severity_fixes)} ✅"
            )

        # Missing data check
        overall_missing_pct = missing_data_analysis.get(
            "missing_percentage", 0.0
        )
        _check_quality_metric(
            overall_missing_pct > max_missing_data_pct,
            f"Missing data: {overall_missing_pct:.1f}%/{max_missing_data_pct}%",
            f"Missing data percentage ({overall_missing_pct:.1f}%) exceeds threshold ({max_missing_data_pct}%)",
            blocking_issues,
            decision_factors,
        )

        # Target column check
        if require_target_column:
            if not target_column:
                blocking_issues.append(
                    "Target column required but not specified"
                )
                decision_factors.append("Target column: Not specified ❌")
            elif target_column not in column_profiles:
                blocking_issues.append(
                    f"Required target column '{target_column}' not found"
                )
                decision_factors.append(
                    f"Target column '{target_column}': Missing ❌"
                )
            else:
                target_missing_pct = column_profiles[target_column].get(
                    "null_percentage", 0.0
                )
                if target_missing_pct > 50:
                    blocking_issues.append(
                        f"Target column '{target_column}' has {target_missing_pct:.1f}% missing values"
                    )
                    decision_factors.append(
                        f"Target column '{target_column}': {target_missing_pct:.1f}% missing ❌"
                    )
                else:
                    decision_factors.append(
                        f"Target column '{target_column}': Present ✅"
                    )

        # Generate recommendations
        recommendations = _generate_recommendations(
            quality_score, fixes, overall_missing_pct, min_quality_score
        )

        # Make decision
        passed = len(blocking_issues) == 0
        decision_reason = (
            f"All quality checks passed. {', '.join(decision_factors)}"
            if passed
            else f"Quality gate failed. Issues: {'; '.join(blocking_issues)}"
        )

        logger.info(
            "✅ Quality gate PASSED" if passed else "❌ Quality gate FAILED"
        )
        if not passed:
            logger.warning(f"Blocking issues: {blocking_issues}")

        return QualityGateDecision(
            passed=passed,
            quality_score=quality_score,
            decision_reason=decision_reason,
            blocking_issues=blocking_issues,
            recommendations=recommendations,
            metadata={
                "decision_factors": decision_factors,
                "thresholds": {
                    "min_quality_score": min_quality_score,
                    "max_missing_data_pct": max_missing_data_pct,
                    "block_on_high_severity": block_on_high_severity,
                    "require_target_column": require_target_column,
                },
                "metrics": {
                    "overall_missing_pct": overall_missing_pct,
                    "high_severity_count": len(high_severity_fixes),
                    "total_fixes": len(fixes),
                    "column_count": len(column_profiles),
                },
            },
        )

    except Exception as e:
        logger.error(f"Quality gate evaluation failed: {e}")
        return QualityGateDecision(
            passed=False,
            quality_score=0.0,
            decision_reason=f"Quality gate evaluation failed: {str(e)}",
            blocking_issues=[f"Technical error: {str(e)}"],
            recommendations=[
                "Review EDA report format and quality gate configuration"
            ],
            metadata={"error": str(e)},
        )


def _generate_recommendations(
    quality_score: float,
    fixes: list,
    overall_missing_pct: float,
    min_threshold: float,
) -> list:
    """Generate actionable recommendations based on quality assessment."""
    recommendations = []

    # Quality score recommendations
    score_gap = min_threshold - quality_score
    if score_gap > 30:
        recommendations.append(
            "Consider alternative data sources due to significant quality issues"
        )
    elif score_gap > 15:
        recommendations.append(
            "Address high-priority data quality issues before proceeding"
        )
    elif score_gap > 0:
        recommendations.append("Minor quality improvements recommended")

    # Critical fixes
    critical_fixes = [
        f for f in fixes if f.get("severity") in ["high", "critical"]
    ]
    if critical_fixes:
        recommendations.append(
            f"Implement {len(critical_fixes)} critical data quality fixes"
        )

        # Add specific fix types
        fix_types = {
            "missing": "Consider imputation strategies for missing data",
            "duplicate": "Remove or consolidate duplicate records",
            "outlier": "Investigate and handle outlier values",
        }

        for fix in critical_fixes[:3]:
            title = fix.get("title", "").lower()
            for keyword, recommendation in fix_types.items():
                if keyword in title and recommendation not in recommendations:
                    recommendations.append(recommendation)
                    break

    # Missing data recommendations
    if overall_missing_pct > 20:
        recommendations.append(
            "High missing data detected - consider imputation or collection improvements"
        )
    elif overall_missing_pct > 10:
        recommendations.append(
            "Moderate missing data - review imputation strategies"
        )

    # Pipeline recommendations
    if quality_score >= min_threshold and not critical_fixes:
        recommendations.extend(
            [
                "Data quality acceptable for downstream processing",
                "Consider implementing quality monitoring",
            ]
        )
    elif score_gap <= min_threshold * 0.2:  # Close to passing
        recommendations.append(
            "Data quality borderline - implement fixes and re-evaluate"
        )
    else:
        recommendations.append(
            "Significant quality issues require attention before production use"
        )

    return recommendations


@step
def evaluate_quality_gate_with_routing(
    report_json: Dict[str, Any],
    min_quality_score: float = 70.0,
    block_on_high_severity: bool = True,
    max_missing_data_pct: float = 30.0,
    require_target_column: bool = False,
    target_column: str = None,
) -> Tuple[
    Annotated[QualityGateDecision, "quality_gate_decision"],
    Annotated[str, "routing_message"],
]:
    """Combined quality gate evaluation and routing decision."""
    decision = evaluate_quality_gate(
        report_json,
        min_quality_score,
        block_on_high_severity,
        max_missing_data_pct,
        require_target_column,
        target_column,
    )

    routing_message = (
        "🚀 Data quality passed - proceed to downstream processing"
        if decision.passed
        else "🛑 Data quality insufficient - review and improve data before proceeding"
    )

    logger.info(routing_message) if decision.passed else logger.warning(
        routing_message
    )
    return decision, routing_message
