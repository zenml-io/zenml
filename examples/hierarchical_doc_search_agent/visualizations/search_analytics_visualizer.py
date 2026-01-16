"""Visualizers for search analytics and agent performance data."""

import html
from typing import Dict, Any, List

from zenml.types import HTMLString


def visualize_search_analytics(analytics_data: Dict[str, Any]) -> HTMLString:
    """Generate HTML visualization for search analytics.

    Args:
        analytics_data: Dictionary containing search analytics data

    Returns:
        HTML string containing the visualization
    """
    total_docs = analytics_data.get('total_documents_visited', 0)
    unique_docs = analytics_data.get('unique_documents_visited', 0)
    efficiency = analytics_data.get('efficiency_score', 0)
    overlap_pct = analytics_data.get('agent_overlap_percentage', 0)

    # Calculate efficiency color
    if efficiency >= 0.8:
        efficiency_color = "#22C55E"
    elif efficiency >= 0.6:
        efficiency_color = "#F59E0B"
    else:
        efficiency_color = "#EF4444"

    html_content = f"""
    <div class="dr-container" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">
        <style>
            .dr-container {{ padding: 20px; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .dr-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
            .dr-h1 {{ font-size: 24px; font-weight: 700; margin: 0; color: #111827; }}
            .dr-h3 {{ font-size: 16px; font-weight: 600; margin: 0 0 12px 0; color: #374151; }}
            .analytics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
            .analytics-card {{ padding: 20px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; text-align: center; }}
            .analytics-value {{ font-size: 32px; font-weight: 800; color: {efficiency_color}; }}
            .analytics-label {{ font-size: 14px; color: #6b7280; margin-top: 8px; }}
            .efficiency-bar {{ width: 100%; height: 20px; background: #e5e7eb; border-radius: 10px; overflow: hidden; margin-top: 12px; }}
            .efficiency-fill {{ height: 100%; background: linear-gradient(90deg, {efficiency_color}, {efficiency_color}99); border-radius: 10px; }}
            .overlap-indicator {{ display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px; }}
            .overlap-circle {{ width: 12px; height: 12px; border-radius: 50%; background: {'#22C55E' if overlap_pct > 20 else '#EF4444'}; }}
        </style>

        <div class="dr-header">
            <span style="font-size: 32px;">📈</span>
            <h1 class="dr-h1">Search Analytics</h1>
        </div>

        <div class="analytics-grid">
            <div class="analytics-card">
                <div class="analytics-value">{total_docs}</div>
                <div class="analytics-label">Total Documents Visited</div>
            </div>

            <div class="analytics-card">
                <div class="analytics-value">{unique_docs}</div>
                <div class="analytics-label">Unique Documents Found</div>
            </div>

            <div class="analytics-card">
                <div class="analytics-value">{efficiency:.1%}</div>
                <div class="analytics-label">Search Efficiency</div>
                <div class="efficiency-bar">
                    <div class="efficiency-fill" style="width: {efficiency * 100}%;"></div>
                </div>
            </div>

            <div class="analytics-card">
                <div class="analytics-value">{overlap_pct:.1f}%</div>
                <div class="analytics-label">Agent Overlap</div>
                <div class="overlap-indicator">
                    <div class="overlap-circle"></div>
                    <span style="font-size: 12px; color: #6b7280;">
                        {'Good coverage' if overlap_pct > 20 else 'Low overlap'}
                    </span>
                </div>
            </div>
        </div>
    </div>
    """

    return HTMLString(html_content)


def visualize_agent_performance(agent_summaries: List[Dict[str, Any]]) -> HTMLString:
    """Generate HTML visualization for agent performance comparison.

    Args:
        agent_summaries: List of agent performance summaries

    Returns:
        HTML string containing the visualization
    """
    if not agent_summaries:
        return HTMLString("<div>No agent performance data available.</div>")

    # Build agent cards
    agent_cards = []
    max_docs = max([summary.get('documents_visited', 0) for summary in agent_summaries], default=1)

    for i, summary in enumerate(agent_summaries):
        docs_visited = summary.get('documents_visited', 0)
        evidence_count = summary.get('evidence_pieces', 0)
        avg_relevance = summary.get('average_relevance', 0)
        status = summary.get('completion_status', 'unknown')
        seed_doc = summary.get('seed_document', {})

        # Status colors
        status_colors = {
            "completed": "#22C55E",
            "budget_exhausted": "#F59E0B",
            "max_depth_reached": "#3B82F6",
            "failed": "#EF4444"
        }
        status_color = status_colors.get(status, "#6B7280")

        # Seed document info
        if isinstance(seed_doc, dict):
            seed_id = seed_doc.get('document_id', 'Unknown')
            seed_score = seed_doc.get('relevance_score', 0)
        else:
            seed_id = str(seed_doc)
            seed_score = 0

        agent_cards.append(f"""
        <div class="agent-card">
            <div class="agent-header">
                <h3 class="agent-title">🤖 Agent {i + 1}</h3>
                <span class="status-badge" style="background: {status_color};">{status.replace('_', ' ').title()}</span>
            </div>

            <div class="agent-metrics">
                <div class="metric-row">
                    <span class="metric-label">Documents Explored:</span>
                    <span class="metric-value">{docs_visited}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(docs_visited / max_docs) * 100}%; background: {status_color};"></div>
                </div>

                <div class="metric-row">
                    <span class="metric-label">Evidence Collected:</span>
                    <span class="metric-value">{evidence_count}</span>
                </div>

                <div class="metric-row">
                    <span class="metric-label">Avg. Relevance:</span>
                    <span class="metric-value">{avg_relevance:.2f}</span>
                </div>
            </div>

            <div class="seed-info">
                <div class="seed-header">🌱 Seed Document</div>
                <div class="seed-id">{html.escape(str(seed_id))}</div>
                <div class="seed-score">Relevance: {seed_score:.2f}</div>
            </div>
        </div>
        """)

    html_content = f"""
    <div class="dr-container" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;">
        <style>
            .dr-container {{ padding: 20px; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .dr-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
            .dr-h1 {{ font-size: 24px; font-weight: 700; margin: 0; color: #111827; }}
            .agents-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
            .agent-card {{ padding: 16px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }}
            .agent-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
            .agent-title {{ font-size: 16px; font-weight: 600; margin: 0; color: #111827; }}
            .status-badge {{ color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
            .agent-metrics {{ margin-bottom: 16px; }}
            .metric-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
            .metric-label {{ font-size: 13px; color: #6b7280; }}
            .metric-value {{ font-weight: 600; color: #111827; }}
            .progress-bar {{ width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin: 4px 0 12px 0; }}
            .progress-fill {{ height: 100%; border-radius: 4px; }}
            .seed-info {{ padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb; }}
            .seed-header {{ font-size: 12px; font-weight: 600; color: #6b7280; margin-bottom: 6px; }}
            .seed-id {{ font-size: 13px; color: #111827; font-weight: 500; }}
            .seed-score {{ font-size: 11px; color: #6b7280; margin-top: 2px; }}
        </style>

        <div class="dr-header">
            <span style="font-size: 32px;">👥</span>
            <h1 class="dr-h1">Agent Performance ({len(agent_summaries)} agents)</h1>
        </div>

        <div class="agents-grid">
            {''.join(agent_cards)}
        </div>
    </div>
    """

    return HTMLString(html_content)