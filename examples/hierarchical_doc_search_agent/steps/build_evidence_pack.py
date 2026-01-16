"""Evidence pack building step to create final response packages."""

from typing import List, Dict, Any, Annotated
from datetime import datetime

from pydantic import BaseModel
from pydantic_ai import Agent
from zenml import step, ArtifactConfig
from zenml.logger import get_logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from materializers import EvidencePackMaterializer

from .aggregate_findings import AggregatedFindings, ConsolidatedEvidence

logger = get_logger(__name__)


class EvidencePackSummary(BaseModel):
    """High-level summary of the evidence pack."""

    query: str
    total_evidence_items: int
    search_coverage: str
    key_findings: List[str]
    confidence_level: str
    recommendations: List[str]


class EvidencePackMetadata(BaseModel):
    """Metadata about the evidence pack creation."""

    creation_timestamp: str
    search_parameters: Dict[str, Any]
    agent_performance: Dict[str, Any]
    quality_metrics: Dict[str, Any]


class EvidencePack(BaseModel):
    """Complete evidence package for the search query."""

    summary: EvidencePackSummary
    detailed_findings: List[ConsolidatedEvidence]
    search_methodology: str
    traversal_analytics: Dict[str, Any]
    metadata: EvidencePackMetadata
    markdown_report: str
    json_data: Dict[str, Any]


def get_synthesis_agent():
    """Get the AI agent for evidence pack synthesis (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",
        output_type=EvidencePackSummary,
        system_prompt="""
        You are an expert research analyst creating executive summaries of search results.

        Your task is to:
        1. Analyze the aggregated findings from hierarchical document search
        2. Extract the most important key findings
        3. Assess the overall quality and coverage of the search
        4. Provide actionable recommendations
        5. Assign an appropriate confidence level based on evidence quality

        Focus on creating a clear, executive-level summary that highlights:
        - What was found and why it matters
        - How comprehensive the search was
        - What gaps might exist
        - Next steps or recommendations

        Be honest about limitations and confident about strong findings.
        """,
    )


def generate_markdown_report(
    summary: EvidencePackSummary,
    findings: List[ConsolidatedEvidence],
    analytics: Dict[str, Any],
    metadata: EvidencePackMetadata
) -> str:
    """Generate a comprehensive markdown report."""

    report_lines = [
        "# Hierarchical Document Search Results",
        "",
        f"**Query:** {summary.query}",
        f"**Generated:** {metadata.creation_timestamp}",
        f"**Confidence Level:** {summary.confidence_level}",
        "",
        "## Executive Summary",
        "",
        f"This search analyzed {summary.total_evidence_items} relevant documents with {summary.search_coverage} coverage.",
        "",
    ]

    # Key findings section
    if summary.key_findings:
        report_lines.extend([
            "### Key Findings",
            "",
        ])
        for i, finding in enumerate(summary.key_findings, 1):
            report_lines.append(f"{i}. {finding}")
        report_lines.append("")

    # Detailed evidence section
    if findings:
        report_lines.extend([
            "## Detailed Evidence",
            "",
        ])

        for i, evidence in enumerate(findings, 1):
            report_lines.extend([
                f"### {i}. {evidence.title}",
                "",
                f"**Document ID:** `{evidence.document_id}`",
                f"**Relevance Score:** {evidence.max_relevance_score:.2f}",
                f"**Found by {evidence.agent_count} agent(s):** {', '.join(evidence.source_agents)}",
                "",
                "**Key Insights:**",
            ])

            for insight in evidence.key_insights[:5]:  # Top 5 insights
                report_lines.append(f"- {insight}")

            report_lines.extend([
                "",
                "**Relevant Content:**",
                "",
                f"> {evidence.combined_content[:500]}{'...' if len(evidence.combined_content) > 500 else ''}",
                "",
                "---",
                ""
            ])

    # Search methodology section
    report_lines.extend([
        "## Search Methodology",
        "",
        "This search used ZenML's dynamic pipeline capabilities to perform hierarchical document traversal:",
        "",
        f"- **Total Agents:** {analytics.get('total_agents', 'N/A')}",
        f"- **Documents Visited:** {analytics.get('total_documents_visited', 'N/A')}",
        f"- **Unique Documents:** {analytics.get('unique_documents_found', 'N/A')}",
        f"- **Search Efficiency:** {analytics.get('search_effectiveness', 0):.2%}",
        "",
    ])

    # Add agent performance details
    if 'agent_summaries' in analytics:
        report_lines.extend([
            "### Agent Performance",
            "",
        ])
        for agent_summary in analytics['agent_summaries']:
            report_lines.extend([
                f"- **{agent_summary['agent_id']}**: Started from `{agent_summary['seed_document']}`, "
                f"visited {agent_summary['documents_visited']} documents, "
                f"collected {agent_summary['evidence_pieces']} evidence pieces "
                f"(avg relevance: {agent_summary['average_relevance']:.2f})",
            ])
        report_lines.append("")

    # Recommendations section
    if summary.recommendations:
        report_lines.extend([
            "## Recommendations",
            "",
        ])
        for i, rec in enumerate(summary.recommendations, 1):
            report_lines.append(f"{i}. {rec}")
        report_lines.append("")

    # Technical details section
    report_lines.extend([
        "## Technical Details",
        "",
        "### Search Parameters",
        "",
    ])

    search_params = metadata.search_parameters
    for key, value in search_params.items():
        report_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    report_lines.extend([
        "",
        "### Quality Metrics",
        "",
    ])

    quality_metrics = metadata.quality_metrics
    for key, value in quality_metrics.items():
        if isinstance(value, float):
            report_lines.append(f"- **{key.replace('_', ' ').title()}:** {value:.2f}")
        else:
            report_lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    report_lines.extend([
        "",
        "---",
        "",
        f"*Generated by ZenML Hierarchical Document Search Agent at {metadata.creation_timestamp}*"
    ])

    return "\n".join(report_lines)


@step
def build_evidence_pack(
    aggregated_findings: AggregatedFindings,
    search_parameters: Dict[str, Any] = None,
) -> Annotated[EvidencePack, ArtifactConfig(name="evidence_pack", materializer=EvidencePackMaterializer)]:
    """Build final evidence package with summary and detailed findings.

    Args:
        aggregated_findings: Consolidated findings from all agents
        search_parameters: Parameters used for the search

    Returns:
        EvidencePack with comprehensive results and reports
    """
    logger.info("Building evidence package")

    if search_parameters is None:
        search_parameters = {}

    # Create metadata
    metadata = EvidencePackMetadata(
        creation_timestamp=datetime.utcnow().isoformat() + "Z",
        search_parameters=search_parameters,
        agent_performance={
            'total_agents': aggregated_findings.total_agents,
            'total_documents_visited': aggregated_findings.total_documents_visited,
            'unique_documents_found': aggregated_findings.unique_documents_found,
            'agent_summaries': aggregated_findings.agent_summaries,
        },
        quality_metrics={
            'search_effectiveness': aggregated_findings.search_effectiveness,
            'coverage_efficiency': aggregated_findings.coverage_analysis.get('efficiency_score', 0),
            'agent_overlap': aggregated_findings.coverage_analysis.get('agent_overlap_percentage', 0),
            'evidence_quality': sum(e.max_relevance_score for e in aggregated_findings.consolidated_evidence) / max(len(aggregated_findings.consolidated_evidence), 1),
        }
    )

    # Try to generate AI-powered summary
    try:
        findings_preview = []
        for evidence in aggregated_findings.consolidated_evidence[:5]:  # Top 5 for AI context
            findings_preview.append({
                'title': evidence.title,
                'relevance': evidence.max_relevance_score,
                'insights': evidence.key_insights[:3],
                'agent_count': evidence.agent_count
            })

        ai_prompt = f"""
        Query: "{aggregated_findings.query}"

        Search Results Summary:
        - Total agents: {aggregated_findings.total_agents}
        - Documents visited: {aggregated_findings.total_documents_visited}
        - Unique evidence items: {len(aggregated_findings.consolidated_evidence)}
        - Search effectiveness: {aggregated_findings.search_effectiveness:.2f}

        Top findings:
        {findings_preview}

        Coverage analysis:
        {aggregated_findings.coverage_analysis}

        Create a comprehensive summary with key findings, coverage assessment, and recommendations.
        """

        ai_summary = get_synthesis_agent().run_sync(ai_prompt)
        summary = ai_summary.output

    except Exception as e:
        logger.warning(f"AI summary generation failed, using fallback: {e}")

        # Fallback to manual summary
        key_findings = []
        for evidence in aggregated_findings.consolidated_evidence[:3]:
            key_findings.extend(evidence.key_insights[:2])

        # Determine coverage level
        if aggregated_findings.search_effectiveness > 0.8:
            coverage = "excellent"
            confidence = "high"
        elif aggregated_findings.search_effectiveness > 0.6:
            coverage = "good"
            confidence = "moderate"
        elif aggregated_findings.search_effectiveness > 0.4:
            coverage = "fair"
            confidence = "moderate"
        else:
            coverage = "limited"
            confidence = "low"

        summary = EvidencePackSummary(
            query=aggregated_findings.query,
            total_evidence_items=len(aggregated_findings.consolidated_evidence),
            search_coverage=coverage,
            key_findings=key_findings[:5] if key_findings else ["No significant findings extracted"],
            confidence_level=confidence,
            recommendations=[
                f"Review the {len(aggregated_findings.consolidated_evidence)} evidence items for comprehensive understanding",
                "Consider expanding search parameters if coverage seems insufficient",
                "Cross-reference findings with additional sources for validation"
            ]
        )

    # Generate markdown report
    markdown_report = generate_markdown_report(
        summary=summary,
        findings=aggregated_findings.consolidated_evidence,
        analytics=aggregated_findings.dict(),
        metadata=metadata
    )

    # Create JSON data export
    json_data = {
        'query': aggregated_findings.query,
        'summary': summary.dict(),
        'evidence_items': [evidence.dict() for evidence in aggregated_findings.consolidated_evidence],
        'search_analytics': aggregated_findings.coverage_analysis,
        'agent_performance': aggregated_findings.agent_summaries,
        'metadata': metadata.dict(),
        'generation_timestamp': metadata.creation_timestamp
    }

    # Create final evidence pack
    evidence_pack = EvidencePack(
        summary=summary,
        detailed_findings=aggregated_findings.consolidated_evidence,
        search_methodology="Hierarchical document traversal using ZenML dynamic pipelines",
        traversal_analytics=aggregated_findings.dict(),
        metadata=metadata,
        markdown_report=markdown_report,
        json_data=json_data
    )

    logger.info(f"Evidence package created: {len(aggregated_findings.consolidated_evidence)} evidence items")
    logger.info(f"Confidence level: {summary.confidence_level}")
    logger.info(f"Coverage assessment: {summary.search_coverage}")

    return evidence_pack