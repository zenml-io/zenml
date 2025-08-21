"""Quality gate step for data quality assessment and pipeline routing.

Evaluates EDA results against quality thresholds to make pass/fail decisions
for downstream processing or model training workflows.
"""

import logging
from typing import Annotated, Any, Dict

from models import QualityGateDecision

from zenml import step

logger = logging.getLogger(__name__)


@step
def evaluate_quality_gate(
    report_json: Dict[str, Any],
    min_quality_score: float = 70.0,
    block_on_high_severity: bool = True,
    max_missing_data_pct: float = 30.0,
    require_target_column: bool = False,
    target_column: str = None,
) -> Annotated[QualityGateDecision, "quality_gate_decision"]:
    """Evaluate data quality and make gate pass/fail decision.

    Analyzes the EDA report results against configurable quality thresholds
    to determine if the data meets requirements for downstream processing.

    Args:
        report_json: EDA report JSON containing quality metrics and findings
        min_quality_score: Minimum data quality score required (0-100)
        block_on_high_severity: Whether to fail on high-severity issues
        max_missing_data_pct: Maximum allowable missing data percentage
        require_target_column: Whether a target column is required
        target_column: Expected target column name (if required)

    Returns:
        QualityGateDecision with pass/fail result and recommendations
    """
    logger.info("Evaluating data quality gate")

    try:
        # Extract key metrics from report
        quality_score = report_json.get("data_quality_score", 0.0)
        fixes = report_json.get("fixes", [])
        missing_data_analysis = report_json.get("missing_data_analysis", {})
        column_profiles = report_json.get("column_profiles", {})

        # Initialize decision components
        blocking_issues = []
        recommendations = []
        decision_factors = []

        # Check 1: Overall quality score
        if quality_score < min_quality_score:
            blocking_issues.append(
                f"Data quality score ({quality_score:.1f}) below minimum threshold ({min_quality_score})"
            )
            decision_factors.append(
                f"Quality score: {quality_score:.1f}/{min_quality_score} ❌"
            )
        else:
            decision_factors.append(
                f"Quality score: {quality_score:.1f}/{min_quality_score} ✅"
            )

        # Check 2: High severity issues
        high_severity_fixes = [
            fix for fix in fixes if fix.get("severity") == "high"
        ]
        if block_on_high_severity and high_severity_fixes:
            high_severity_titles = [
                fix.get("title", "Unknown issue")
                for fix in high_severity_fixes
            ]
            blocking_issues.append(
                f"High severity issues found: {', '.join(high_severity_titles)}"
            )
            decision_factors.append(
                f"High severity issues: {len(high_severity_fixes)} ❌"
            )
        else:
            decision_factors.append(
                f"High severity issues: {len(high_severity_fixes)} ✅"
            )

        # Check 3: Missing data threshold
        overall_missing_pct = missing_data_analysis.get(
            "missing_percentage", 0.0
        )
        if overall_missing_pct > max_missing_data_pct:
            blocking_issues.append(
                f"Missing data percentage ({overall_missing_pct:.1f}%) exceeds threshold ({max_missing_data_pct}%)"
            )
            decision_factors.append(
                f"Missing data: {overall_missing_pct:.1f}%/{max_missing_data_pct}% ❌"
            )
        else:
            decision_factors.append(
                f"Missing data: {overall_missing_pct:.1f}%/{max_missing_data_pct}% ✅"
            )

        # Check 4: Target column requirement
        if require_target_column and target_column:
            if target_column not in column_profiles:
                blocking_issues.append(
                    f"Required target column '{target_column}' not found in dataset"
                )
                decision_factors.append(
                    f"Target column '{target_column}': Missing ❌"
                )
            else:
                # Check target column quality
                target_profile = column_profiles[target_column]
                target_missing_pct = target_profile.get("null_percentage", 0.0)

                if (
                    target_missing_pct > 50
                ):  # Target column shouldn't be mostly empty
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

        # Generate recommendations based on findings
        recommendations = _generate_recommendations(
            quality_score,
            fixes,
            missing_data_analysis,
            column_profiles,
            min_quality_score,
        )

        # Make final decision
        passed = len(blocking_issues) == 0

        if passed:
            decision_reason = (
                f"All quality checks passed. {', '.join(decision_factors)}"
            )
            logger.info("✅ Quality gate PASSED")
        else:
            decision_reason = f"Quality gate failed. Blocking issues: {'; '.join(blocking_issues)}"
            logger.warning("❌ Quality gate FAILED")

        # Log decision details
        logger.info(f"Quality score: {quality_score:.1f}")
        logger.info(f"Missing data: {overall_missing_pct:.1f}%")
        logger.info(f"High severity issues: {len(high_severity_fixes)}")

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

        # Return failure decision
        return QualityGateDecision(
            passed=False,
            quality_score=0.0,
            decision_reason=f"Quality gate evaluation failed: {str(e)}",
            blocking_issues=[f"Technical error during evaluation: {str(e)}"],
            recommendations=[
                "Review EDA report format and quality gate configuration"
            ],
            metadata={"error": str(e)},
        )


def _generate_recommendations(
    quality_score: float,
    fixes: list,
    missing_data_analysis: dict,
    column_profiles: dict,
    min_threshold: float,
) -> list:
    """Generate actionable recommendations based on quality assessment."""
    recommendations = []

    # Score-based recommendations
    if quality_score < min_threshold:
        score_gap = min_threshold - quality_score
        if score_gap > 30:
            recommendations.append(
                "Consider data cleaning or alternative data sources due to significant quality issues"
            )
        elif score_gap > 15:
            recommendations.append(
                "Address high-priority data quality issues before proceeding"
            )
        else:
            recommendations.append(
                "Minor quality improvements recommended but data is usable"
            )

    # Fix-based recommendations
    critical_fixes = [
        fix for fix in fixes if fix.get("severity") in ["high", "critical"]
    ]
    if critical_fixes:
        recommendations.append(
            f"Implement {len(critical_fixes)} critical data quality fixes"
        )

        # Add specific recommendations for common issues
        for fix in critical_fixes[:3]:  # Top 3 critical fixes
            if "missing" in fix.get("title", "").lower():
                recommendations.append(
                    "Consider imputation strategies for missing data"
                )
            elif "duplicate" in fix.get("title", "").lower():
                recommendations.append(
                    "Remove or consolidate duplicate records"
                )
            elif "outlier" in fix.get("title", "").lower():
                recommendations.append("Investigate and handle outlier values")

    # Missing data recommendations
    overall_missing_pct = missing_data_analysis.get("missing_percentage", 0.0)
    if overall_missing_pct > 20:
        recommendations.append(
            "High missing data detected - consider data imputation or collection improvements"
        )
    elif overall_missing_pct > 10:
        recommendations.append(
            "Moderate missing data - review imputation strategies"
        )

    # Column-specific recommendations
    if column_profiles:
        high_missing_cols = [
            col
            for col, profile in column_profiles.items()
            if profile.get("null_percentage", 0) > 50
        ]

        if high_missing_cols:
            if len(high_missing_cols) == 1:
                recommendations.append(
                    f"Column '{high_missing_cols[0]}' has excessive missing data - consider removal or targeted collection"
                )
            else:
                recommendations.append(
                    f"{len(high_missing_cols)} columns have >50% missing data - review data collection process"
                )

    # Pipeline-specific recommendations
    if quality_score >= min_threshold and len(critical_fixes) == 0:
        recommendations.append(
            "Data quality is acceptable for downstream processing"
        )
        recommendations.append(
            "Consider implementing monitoring for quality regression"
        )
    elif quality_score >= min_threshold * 0.8:  # Close to passing
        recommendations.append(
            "Data quality is borderline - implement fixes and re-evaluate"
        )
        recommendations.append(
            "Consider A/B testing with and without quality improvements"
        )
    else:
        recommendations.append(
            "Significant data quality issues require attention before production use"
        )
        recommendations.append(
            "Consider data pipeline improvements or alternative data sources"
        )

    return recommendations


@step
def route_based_on_quality(
    decision: QualityGateDecision,
    on_pass_message: str = "Proceed to downstream processing",
    on_fail_message: str = "Data quality insufficient - halt pipeline",
) -> Annotated[str, "routing_decision"]:
    """Route pipeline execution based on quality gate decision.

    Simple routing step that can be used to conditionally execute
    downstream steps based on quality gate results.

    Args:
        decision: Quality gate decision result
        on_pass_message: Message when quality gate passes
        on_fail_message: Message when quality gate fails

    Returns:
        Routing message indicating next steps
    """
    if decision.passed:
        logger.info(f"🚀 {on_pass_message}")
        return on_pass_message
    else:
        logger.warning(f"🛑 {on_fail_message}")
        return on_fail_message
