"""Visualizers for evidence packages and search artifacts."""

import html
from typing import List
from datetime import datetime

from zenml.types import HTMLString
from steps.build_evidence_pack import EvidencePack
from steps.traverse_node import TraversalTrace
from steps.intent_detection import SearchIntent


def visualize_search_intent(search_intent: SearchIntent) -> HTMLString:
    """Generate HTML visualization for search intent analysis.

    Args:
        search_intent: The SearchIntent object to visualize

    Returns:
        HTML string containing the visualization
    """
    # Determine search type color and icon
    search_type_color = "#22C55E" if search_intent.search_type == "deep" else "#3B82F6"
    search_icon = "🔍" if search_intent.search_type == "deep" else "📖"

    # Build key concepts list
    concepts_html = ""
    if search_intent.key_concepts:
        concepts_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">💡 Key Concepts</h3>
            <div class="concepts-grid">
                {" ".join([f'<span class="concept-badge">{html.escape(concept)}</span>' for concept in search_intent.key_concepts])}
            </div>
        </div>
        """

    # Build complexity factors
    factors_html = ""
    if hasattr(search_intent, 'complexity_factors') and search_intent.complexity_factors:
        factors_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">⚙️ Complexity Factors</h3>
            <div class="factors-list">
                {" ".join([f'<div class="factor-item">• {html.escape(factor)}</div>' for factor in search_intent.complexity_factors])}
            </div>
        </div>
        """

    html_content = f"""
    <div class="dr-container" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">
        <style>
            .dr-container {{ padding: 20px; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .dr-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
            .dr-h1 {{ font-size: 24px; font-weight: 700; margin: 0; color: #111827; }}
            .dr-h3 {{ font-size: 16px; font-weight: 600; margin: 0 0 12px 0; color: #374151; }}
            .dr-section {{ margin: 16px 0; padding: 16px; background: #f9fafb; border-radius: 6px; border-left: 4px solid {search_type_color}; }}
            .dr-badge {{ padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; }}
            .search-type-badge {{ background: {search_type_color}; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 600; }}
            .confidence-bar {{ width: 100%; height: 20px; background: #e5e7eb; border-radius: 10px; overflow: hidden; margin-top: 8px; }}
            .confidence-fill {{ height: 100%; background: linear-gradient(90deg, {search_type_color}, {search_type_color}99); border-radius: 10px; }}
            .concept-badge {{ display: inline-block; background: #dbeafe; color: #1e40af; padding: 4px 10px; margin: 2px; border-radius: 12px; font-size: 12px; }}
            .concepts-grid {{ display: flex; flex-wrap: wrap; gap: 4px; }}
            .factor-item {{ margin: 4px 0; color: #6b7280; }}
            .query-text {{ font-style: italic; color: #6b7280; background: #f3f4f6; padding: 12px; border-radius: 6px; margin: 8px 0; }}
        </style>

        <div class="dr-header">
            <span style="font-size: 32px;">{search_icon}</span>
            <div>
                <h1 class="dr-h1">Search Intent Analysis</h1>
                <span class="search-type-badge">{search_intent.search_type.upper()} SEARCH</span>
            </div>
        </div>

        <div class="dr-section">
            <h3 class="dr-h3">📝 Query</h3>
            <div class="query-text">"{html.escape(search_intent.query)}"</div>
        </div>

        <div class="dr-section">
            <h3 class="dr-h3">🎯 Confidence Score</h3>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-weight: 600; color: {search_type_color};">{search_intent.confidence:.1%}</span>
                <div class="confidence-bar" style="flex: 1;">
                    <div class="confidence-fill" style="width: {search_intent.confidence * 100}%;"></div>
                </div>
            </div>
        </div>

        {concepts_html}
        {factors_html}

        <div class="dr-section">
            <h3 class="dr-h3">🔄 Traversal Required</h3>
            <span style="font-size: 20px; color: {'#22C55E' if search_intent.requires_traversal else '#6B7280'};">
                {'✅ Yes - Multi-hop exploration needed' if search_intent.requires_traversal else '❌ No - Direct lookup sufficient'}
            </span>
        </div>
    </div>
    """

    return HTMLString(html_content)


def visualize_traversal_trace(traversal_trace: TraversalTrace) -> HTMLString:
    """Generate HTML visualization for traversal trace.

    Args:
        traversal_trace: The TraversalTrace object to visualize

    Returns:
        HTML string containing the visualization
    """
    # Status color mapping
    status_colors = {
        "completed": "#22C55E",
        "budget_exhausted": "#F59E0B",
        "max_depth_reached": "#3B82F6",
        "failed": "#EF4444",
        "terminated_early": "#8B5CF6"
    }

    status_color = status_colors.get(traversal_trace.completion_status, "#6B7280")

    # Build traversal path
    path_html = ""
    if traversal_trace.traversal_path:
        path_items = []
        for i, doc_id in enumerate(traversal_trace.traversal_path):
            arrow = " → " if i < len(traversal_trace.traversal_path) - 1 else ""
            path_items.append(f'<span class="path-node">{html.escape(doc_id)}</span>{arrow}')
        path_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">🗺️ Traversal Path</h3>
            <div class="traversal-path">{''.join(path_items)}</div>
        </div>
        """

    # Build evidence summary
    evidence_html = ""
    if traversal_trace.evidence_collected:
        evidence_items = []
        for evidence in traversal_trace.evidence_collected[:5]:  # Show top 5
            evidence_items.append(f"""
            <div class="evidence-item">
                <div class="evidence-header">
                    <strong>{html.escape(evidence.title)}</strong>
                    <span class="relevance-score">{evidence.relevance_score:.2f}</span>
                </div>
                <div class="evidence-preview">{html.escape(evidence.relevant_content[:150])}...</div>
            </div>
            """)

        evidence_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">📄 Evidence Collected ({len(traversal_trace.evidence_collected)} items)</h3>
            <div class="evidence-list">{''.join(evidence_items)}</div>
        </div>
        """

    html_content = f"""
    <div class="dr-container" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">
        <style>
            .dr-container {{ padding: 20px; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .dr-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
            .dr-h1 {{ font-size: 24px; font-weight: 700; margin: 0; color: #111827; }}
            .dr-h3 {{ font-size: 16px; font-weight: 600; margin: 0 0 12px 0; color: #374151; }}
            .dr-section {{ margin: 16px 0; padding: 16px; background: #f9fafb; border-radius: 6px; border-left: 4px solid {status_color}; }}
            .status-badge {{ background: {status_color}; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 600; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
            .metric-item {{ text-align: center; padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb; }}
            .metric-value {{ font-size: 20px; font-weight: 700; color: {status_color}; }}
            .metric-label {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
            .path-node {{ background: #e0e7ff; color: #3730a3; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin: 2px; }}
            .traversal-path {{ line-height: 1.8; }}
            .evidence-item {{ margin: 8px 0; padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb; }}
            .evidence-header {{ display: flex; justify-content: between; align-items: center; margin-bottom: 6px; }}
            .relevance-score {{ background: #f0fdf4; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
            .evidence-preview {{ color: #6b7280; font-size: 14px; line-height: 1.4; }}
            .budget-bar {{ width: 100%; height: 16px; background: #e5e7eb; border-radius: 8px; overflow: hidden; }}
            .budget-used {{ height: 100%; background: linear-gradient(90deg, {status_color}, {status_color}99); border-radius: 8px; }}
        </style>

        <div class="dr-header">
            <span style="font-size: 32px;">🤖</span>
            <div>
                <h1 class="dr-h1">Agent Traversal Trace</h1>
                <span class="status-badge">{traversal_trace.completion_status.replace('_', ' ').upper()}</span>
            </div>
        </div>

        <div class="dr-section">
            <h3 class="dr-h3">📊 Performance Metrics</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-value">{traversal_trace.total_steps}</div>
                    <div class="metric-label">Steps Taken</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{traversal_trace.budget_remaining}</div>
                    <div class="metric-label">Budget Remaining</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{len(traversal_trace.visited_documents)}</div>
                    <div class="metric-label">Docs Visited</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{len(traversal_trace.evidence_collected)}</div>
                    <div class="metric-label">Evidence Items</div>
                </div>
            </div>
        </div>

        <div class="dr-section">
            <h3 class="dr-h3">🎯 Budget Utilization</h3>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-weight: 600;">Used: {traversal_trace.total_steps} / {traversal_trace.total_steps + traversal_trace.budget_remaining}</span>
                <div class="budget-bar" style="flex: 1;">
                    <div class="budget-used" style="width: {(traversal_trace.total_steps / max(traversal_trace.total_steps + traversal_trace.budget_remaining, 1)) * 100}%;"></div>
                </div>
            </div>
        </div>

        {path_html}
        {evidence_html}

        <div class="dr-section">
            <h3 class="dr-h3">🌱 Seed Document</h3>
            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                <strong>ID:</strong> {html.escape(traversal_trace.seed_document.document_id)}<br>
                <strong>Relevance:</strong> {traversal_trace.seed_document.relevance_score:.2f}<br>
                <strong>Reasoning:</strong> {html.escape(traversal_trace.seed_document.selection_reasoning)}
            </div>
        </div>
    </div>
    """

    return HTMLString(html_content)


def visualize_evidence_pack(evidence_pack: EvidencePack) -> HTMLString:
    """Generate comprehensive HTML visualization for evidence pack.

    Args:
        evidence_pack: The EvidencePack object to visualize

    Returns:
        HTML string containing the visualization
    """
    # Confidence level colors
    confidence_colors = {
        "high": "#22C55E",
        "moderate": "#F59E0B",
        "low": "#EF4444"
    }

    confidence_color = confidence_colors.get(evidence_pack.summary.confidence_level, "#6B7280")

    # Build key findings
    findings_html = ""
    if evidence_pack.summary.key_findings:
        findings_list = []
        for i, finding in enumerate(evidence_pack.summary.key_findings[:5], 1):
            findings_list.append(f"""
            <div class="finding-item">
                <span class="finding-number">{i}</span>
                <span class="finding-text">{html.escape(finding)}</span>
            </div>
            """)

        findings_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">🎯 Key Findings</h3>
            <div class="findings-list">{''.join(findings_list)}</div>
        </div>
        """

    # Build evidence summary
    evidence_summary_html = ""
    if evidence_pack.detailed_findings:
        evidence_items = []
        for evidence in evidence_pack.detailed_findings[:3]:  # Show top 3
            evidence_items.append(f"""
            <div class="evidence-card">
                <div class="evidence-card-header">
                    <h4 class="evidence-title">{html.escape(evidence.title)}</h4>
                    <div class="evidence-meta">
                        <span class="relevance-badge">{evidence.max_relevance_score:.2f}</span>
                        <span class="agent-badge">{evidence.agent_count} agent(s)</span>
                    </div>
                </div>
                <div class="evidence-insights">
                    {" ".join([f'<span class="insight-tag">• {html.escape(insight[:60])}...</span>' for insight in evidence.key_insights[:2]])}
                </div>
            </div>
            """)

        evidence_summary_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">📚 Evidence Summary ({len(evidence_pack.detailed_findings)} total)</h3>
            <div class="evidence-cards">{''.join(evidence_items)}</div>
        </div>
        """

    # Build recommendations
    recommendations_html = ""
    if evidence_pack.summary.recommendations:
        rec_list = []
        for i, rec in enumerate(evidence_pack.summary.recommendations, 1):
            rec_list.append(f"""
            <div class="recommendation-item">
                <span class="rec-number">{i}</span>
                <span class="rec-text">{html.escape(rec)}</span>
            </div>
            """)

        recommendations_html = f"""
        <div class="dr-section">
            <h3 class="dr-h3">💡 Recommendations</h3>
            <div class="recommendations-list">{''.join(rec_list)}</div>
        </div>
        """

    html_content = f"""
    <div class="dr-container" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">
        <style>
            .dr-container {{ padding: 24px; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
            .dr-header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #f3f4f6; }}
            .dr-h1 {{ font-size: 28px; font-weight: 800; margin: 0; color: #111827; }}
            .dr-h3 {{ font-size: 18px; font-weight: 600; margin: 0 0 16px 0; color: #374151; }}
            .dr-section {{ margin: 20px 0; padding: 20px; background: #f9fafb; border-radius: 8px; border-left: 4px solid {confidence_color}; }}
            .confidence-badge {{ background: {confidence_color}; color: white; padding: 8px 16px; border-radius: 24px; font-weight: 700; text-transform: uppercase; }}
            .coverage-badge {{ background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 16px; font-weight: 600; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin: 16px 0; }}
            .stat-item {{ text-align: center; padding: 16px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .stat-value {{ font-size: 24px; font-weight: 800; color: {confidence_color}; }}
            .stat-label {{ font-size: 13px; color: #6b7280; margin-top: 6px; font-weight: 500; }}
            .finding-item, .recommendation-item {{ display: flex; align-items: flex-start; gap: 12px; margin: 12px 0; padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb; }}
            .finding-number, .rec-number {{ background: {confidence_color}; color: white; width: 24px; height: 24px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }}
            .finding-text, .rec-text {{ line-height: 1.5; color: #374151; }}
            .evidence-card {{ margin: 12px 0; padding: 16px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .evidence-card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
            .evidence-title {{ font-size: 16px; font-weight: 600; color: #111827; margin: 0; }}
            .evidence-meta {{ display: flex; gap: 8px; }}
            .relevance-badge {{ background: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
            .agent-badge {{ background: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
            .evidence-insights {{ display: flex; flex-wrap: wrap; gap: 4px; }}
            .insight-tag {{ background: #f3f4f6; color: #4b5563; padding: 4px 8px; border-radius: 10px; font-size: 11px; }}
            .query-highlight {{ font-style: italic; color: #6366f1; background: #eef2ff; padding: 12px; border-radius: 8px; margin: 12px 0; border-left: 4px solid #6366f1; }}
        </style>

        <div class="dr-header">
            <span style="font-size: 40px;">📋</span>
            <div style="flex: 1;">
                <h1 class="dr-h1">Evidence Package</h1>
                <div style="margin-top: 8px; display: flex; gap: 12px; align-items: center;">
                    <span class="confidence-badge">{evidence_pack.summary.confidence_level} CONFIDENCE</span>
                    <span class="coverage-badge">{evidence_pack.summary.search_coverage} COVERAGE</span>
                </div>
            </div>
        </div>

        <div class="query-highlight">
            <strong>Query:</strong> "{html.escape(evidence_pack.summary.query)}"
        </div>

        <div class="dr-section">
            <h3 class="dr-h3">📊 Search Statistics</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{evidence_pack.summary.total_evidence_items}</div>
                    <div class="stat-label">Evidence Items</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{evidence_pack.traversal_analytics.get('total_agents', 0)}</div>
                    <div class="stat-label">Agents Used</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{evidence_pack.traversal_analytics.get('total_documents_visited', 0)}</div>
                    <div class="stat-label">Docs Visited</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{evidence_pack.traversal_analytics.get('search_effectiveness', 0):.1%}</div>
                    <div class="stat-label">Effectiveness</div>
                </div>
            </div>
        </div>

        {findings_html}
        {evidence_summary_html}
        {recommendations_html}

        <div class="dr-section">
            <h3 class="dr-h3">🔧 Technical Details</h3>
            <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div><strong>Search Methodology:</strong> {html.escape(evidence_pack.search_methodology)}</div>
                <div style="margin-top: 8px;"><strong>Generated:</strong> {evidence_pack.metadata.creation_timestamp}</div>
                <div style="margin-top: 8px;"><strong>Search Type:</strong> {evidence_pack.metadata.search_parameters.get('search_type', 'unknown').title()}</div>
            </div>
        </div>
    </div>
    """

    return HTMLString(html_content)