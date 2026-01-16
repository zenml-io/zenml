"""Custom materializers with built-in visualizations for hierarchical search artifacts."""

import os
import html
from typing import Type, ClassVar, Dict, Any

from zenml.materializers.pydantic_materializer import PydanticMaterializer
from zenml.enums import ArtifactType, VisualizationType


class SearchIntentMaterializer(PydanticMaterializer):
    """Materializer for SearchIntent with custom visualization."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate HTML visualization for search intent."""
        search_type_color = "#22C55E" if data.search_type == "deep" else "#3B82F6"
        search_icon = "&#128269;" if data.search_type == "deep" else "&#128214;"

        concepts_html = ""
        if data.key_concepts:
            concepts_badges = " ".join([
                f'<span style="display:inline-block;background:#dbeafe;color:#1e40af;padding:4px 10px;margin:2px;border-radius:12px;font-size:12px;">{html.escape(c)}</span>'
                for c in data.key_concepts
            ])
            concepts_html = f'''
            <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {search_type_color};">
                <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Key Concepts</h3>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">{concepts_badges}</div>
            </div>
            '''

        html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Search Intent</title></head>
<body>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;padding:20px;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <span style="font-size:32px;">{search_icon}</span>
        <div>
            <h1 style="font-size:24px;font-weight:700;margin:0;color:#111827;">Search Intent Analysis</h1>
            <span style="background:{search_type_color};color:white;padding:6px 14px;border-radius:20px;font-weight:600;text-transform:uppercase;">{data.search_type} SEARCH</span>
        </div>
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {search_type_color};">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Query</h3>
        <div style="font-style:italic;color:#6b7280;background:#f3f4f6;padding:12px;border-radius:6px;">"{html.escape(data.query)}"</div>
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {search_type_color};">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Confidence</h3>
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-weight:600;color:{search_type_color};">{data.confidence:.1%}</span>
            <div style="flex:1;height:20px;background:#e5e7eb;border-radius:10px;overflow:hidden;">
                <div style="height:100%;background:{search_type_color};width:{data.confidence * 100}%;border-radius:10px;"></div>
            </div>
        </div>
    </div>

    {concepts_html}

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {search_type_color};">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Traversal Required</h3>
        <span style="font-size:20px;color:{'#22C55E' if data.requires_traversal else '#6B7280'};">
            {'&#9989; Yes - Multi-hop exploration needed' if data.requires_traversal else '&#10060; No - Direct lookup sufficient'}
        </span>
    </div>
</div>
</body>
</html>'''

        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write(html_content)

        return {visualization_uri: VisualizationType.HTML}


class TraversalPlanMaterializer(PydanticMaterializer):
    """Materializer for TraversalPlan with custom visualization."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate HTML visualization for traversal plan."""
        seeds_html = ""
        if data.seed_documents:
            seed_cards = []
            for i, seed in enumerate(data.seed_documents):
                seed_cards.append(f'''
                <div style="padding:12px;background:white;border-radius:6px;border:1px solid #e5e7eb;margin:8px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="color:#111827;">&#127793; {html.escape(seed.title)}</strong>
                        <span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:12px;font-size:11px;">{seed.relevance_score:.2f}</span>
                    </div>
                    <div style="font-size:12px;color:#6b7280;margin-top:4px;">ID: {html.escape(seed.document_id)}</div>
                </div>
                ''')
            seeds_html = "".join(seed_cards)

        html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Traversal Plan</title></head>
<body>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;padding:20px;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <span style="font-size:32px;">&#128506;</span>
        <div>
            <h1 style="font-size:24px;font-weight:700;margin:0;color:#111827;">Traversal Plan</h1>
            <span style="background:#8B5CF6;color:white;padding:6px 14px;border-radius:20px;font-weight:600;">{len(data.seed_documents)} SEED DOCUMENTS</span>
        </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0;">
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:700;color:#8B5CF6;">{data.max_agents}</div>
            <div style="font-size:12px;color:#6b7280;">Max Agents</div>
        </div>
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:700;color:#8B5CF6;">{data.total_estimated_documents}</div>
            <div style="font-size:12px;color:#6b7280;">Est. Documents</div>
        </div>
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid #8B5CF6;">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Seed Documents</h3>
        {seeds_html if seeds_html else '<div style="color:#6b7280;">No seed documents selected</div>'}
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid #8B5CF6;">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Strategy</h3>
        <div style="color:#374151;">{html.escape(data.search_strategy)}</div>
        <div style="color:#6b7280;margin-top:8px;font-size:14px;">{html.escape(data.reasoning)}</div>
    </div>
</div>
</body>
</html>'''

        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write(html_content)

        return {visualization_uri: VisualizationType.HTML}


class TraversalTraceMaterializer(PydanticMaterializer):
    """Materializer for TraversalTrace with custom visualization."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate HTML visualization for traversal trace."""
        status_colors = {
            "completed": "#22C55E",
            "budget_exhausted": "#F59E0B",
            "max_depth_reached": "#3B82F6",
            "depth_limit_reached": "#3B82F6",
            "failed": "#EF4444",
            "in_progress": "#8B5CF6"
        }
        status_color = status_colors.get(data.completion_status, "#6B7280")

        path_html = ""
        if data.traversal_path:
            path_nodes = []
            for i, step_info in enumerate(data.traversal_path):
                doc_id = step_info.get('document_id', 'unknown')
                arrow = " &#8594; " if i < len(data.traversal_path) - 1 else ""
                path_nodes.append(f'<span style="background:#e0e7ff;color:#3730a3;padding:4px 8px;border-radius:12px;font-size:12px;">{html.escape(doc_id)}</span>{arrow}')
            path_html = "".join(path_nodes)

        evidence_html = ""
        if data.evidence_collected:
            evidence_items = []
            for evidence in data.evidence_collected[:5]:
                evidence_items.append(f'''
                <div style="margin:8px 0;padding:12px;background:white;border-radius:6px;border:1px solid #e5e7eb;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <strong>{html.escape(evidence.title)}</strong>
                        <span style="background:#f0fdf4;color:#166534;padding:2px 8px;border-radius:12px;font-size:12px;">{evidence.relevance_score:.2f}</span>
                    </div>
                    <div style="color:#6b7280;font-size:14px;">{html.escape(evidence.relevant_content[:100])}...</div>
                </div>
                ''')
            evidence_html = "".join(evidence_items)

        html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Traversal Trace</title></head>
<body>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;padding:20px;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <span style="font-size:32px;">&#129302;</span>
        <div>
            <h1 style="font-size:24px;font-weight:700;margin:0;color:#111827;">Agent Traversal Trace</h1>
            <span style="background:{status_color};color:white;padding:6px 14px;border-radius:20px;font-weight:600;">{data.completion_status.replace('_', ' ').upper()}</span>
        </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin:16px 0;">
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:20px;font-weight:700;color:{status_color};">{data.total_steps}</div>
            <div style="font-size:11px;color:#6b7280;">Steps Taken</div>
        </div>
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:20px;font-weight:700;color:{status_color};">{data.budget_remaining}</div>
            <div style="font-size:11px;color:#6b7280;">Budget Left</div>
        </div>
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:20px;font-weight:700;color:{status_color};">{len(data.visited_documents)}</div>
            <div style="font-size:11px;color:#6b7280;">Docs Visited</div>
        </div>
        <div style="text-align:center;padding:12px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:20px;font-weight:700;color:{status_color};">{len(data.evidence_collected)}</div>
            <div style="font-size:11px;color:#6b7280;">Evidence</div>
        </div>
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {status_color};">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Traversal Path</h3>
        <div style="line-height:1.8;">{path_html if path_html else 'No path recorded'}</div>
    </div>

    {f'<div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {status_color};"><h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Evidence Collected ({len(data.evidence_collected)} items)</h3>{evidence_html}</div>' if evidence_html else ''}
</div>
</body>
</html>'''

        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write(html_content)

        return {visualization_uri: VisualizationType.HTML}


class AggregatedFindingsMaterializer(PydanticMaterializer):
    """Materializer for AggregatedFindings with custom visualization."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate HTML visualization for aggregated findings."""
        effectiveness_color = "#22C55E" if data.search_effectiveness > 0.7 else ("#F59E0B" if data.search_effectiveness > 0.4 else "#EF4444")

        evidence_html = ""
        if data.consolidated_evidence:
            evidence_cards = []
            for evidence in data.consolidated_evidence[:5]:
                insights = " ".join([f'<span style="background:#f3f4f6;color:#4b5563;padding:2px 6px;border-radius:8px;font-size:10px;">&#8226; {html.escape(i[:40])}...</span>' for i in evidence.key_insights[:2]]) if evidence.key_insights else ""
                evidence_cards.append(f'''
                <div style="margin:8px 0;padding:12px;background:white;border-radius:6px;border:1px solid #e5e7eb;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <strong style="font-size:14px;">{html.escape(evidence.title)}</strong>
                        <div style="display:flex;gap:4px;">
                            <span style="background:#dcfce7;color:#166534;padding:2px 6px;border-radius:10px;font-size:10px;">{evidence.max_relevance_score:.2f}</span>
                            <span style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:10px;font-size:10px;">{evidence.agent_count} agent(s)</span>
                        </div>
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:4px;">{insights}</div>
                </div>
                ''')
            evidence_html = "".join(evidence_cards)

        html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Aggregated Findings</title></head>
<body>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;padding:20px;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <span style="font-size:32px;">&#128202;</span>
        <div>
            <h1 style="font-size:24px;font-weight:700;margin:0;color:#111827;">Aggregated Findings</h1>
            <span style="background:{effectiveness_color};color:white;padding:6px 14px;border-radius:20px;font-weight:600;">{data.search_effectiveness:.0%} EFFECTIVENESS</span>
        </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:16px 0;">
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:28px;font-weight:700;color:{effectiveness_color};">{data.total_agents}</div>
            <div style="font-size:12px;color:#6b7280;">Agents Used</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:28px;font-weight:700;color:{effectiveness_color};">{data.total_documents_visited}</div>
            <div style="font-size:12px;color:#6b7280;">Docs Visited</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:28px;font-weight:700;color:{effectiveness_color};">{data.unique_documents_found}</div>
            <div style="font-size:12px;color:#6b7280;">Unique Finds</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:6px;border:1px solid #e5e7eb;">
            <div style="font-size:28px;font-weight:700;color:{effectiveness_color};">{len(data.consolidated_evidence)}</div>
            <div style="font-size:12px;color:#6b7280;">Evidence Items</div>
        </div>
    </div>

    <div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {effectiveness_color};">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Query</h3>
        <div style="font-style:italic;color:#6b7280;">"{html.escape(data.query)}"</div>
    </div>

    {f'<div style="margin:16px 0;padding:16px;background:#f9fafb;border-radius:6px;border-left:4px solid {effectiveness_color};"><h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Top Evidence</h3>{evidence_html}</div>' if evidence_html else ''}
</div>
</body>
</html>'''

        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write(html_content)

        return {visualization_uri: VisualizationType.HTML}


class EvidencePackMaterializer(PydanticMaterializer):
    """Materializer for EvidencePack with custom visualization."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Generate HTML visualization for evidence pack."""
        confidence_colors = {"high": "#22C55E", "moderate": "#F59E0B", "low": "#EF4444"}
        confidence_color = confidence_colors.get(data.summary.confidence_level, "#6B7280")

        findings_html = ""
        if data.summary.key_findings:
            findings_items = []
            for i, finding in enumerate(data.summary.key_findings[:5], 1):
                findings_items.append(f'''
                <div style="display:flex;align-items:flex-start;gap:12px;margin:8px 0;padding:12px;background:white;border-radius:6px;border:1px solid #e5e7eb;">
                    <span style="background:{confidence_color};color:white;width:24px;height:24px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;">{i}</span>
                    <span style="line-height:1.5;color:#374151;">{html.escape(finding)}</span>
                </div>
                ''')
            findings_html = "".join(findings_items)

        recommendations_html = ""
        if data.summary.recommendations:
            rec_items = []
            for i, rec in enumerate(data.summary.recommendations, 1):
                rec_items.append(f'''
                <div style="display:flex;align-items:flex-start;gap:12px;margin:8px 0;padding:12px;background:white;border-radius:6px;border:1px solid #e5e7eb;">
                    <span style="background:#3B82F6;color:white;width:24px;height:24px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;">{i}</span>
                    <span style="line-height:1.5;color:#374151;">{html.escape(rec)}</span>
                </div>
                ''')
            recommendations_html = "".join(rec_items)

        html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Evidence Package</title></head>
<body>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;padding:24px;background:#fff;border-radius:12px;border:1px solid #e5e7eb;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;padding-bottom:16px;border-bottom:2px solid #f3f4f6;">
        <span style="font-size:40px;">&#128203;</span>
        <div style="flex:1;">
            <h1 style="font-size:28px;font-weight:800;margin:0;color:#111827;">Evidence Package</h1>
            <div style="margin-top:8px;display:flex;gap:12px;align-items:center;">
                <span style="background:{confidence_color};color:white;padding:8px 16px;border-radius:24px;font-weight:700;text-transform:uppercase;">{data.summary.confidence_level} CONFIDENCE</span>
                <span style="background:#e0e7ff;color:#3730a3;padding:6px 12px;border-radius:16px;font-weight:600;">{data.summary.search_coverage.upper()} COVERAGE</span>
            </div>
        </div>
    </div>

    <div style="font-style:italic;color:#6366f1;background:#eef2ff;padding:12px;border-radius:8px;margin:12px 0;border-left:4px solid #6366f1;">
        <strong>Query:</strong> "{html.escape(data.summary.query)}"
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin:20px 0;">
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:800;color:{confidence_color};">{data.summary.total_evidence_items}</div>
            <div style="font-size:13px;color:#6b7280;margin-top:6px;font-weight:500;">Evidence Items</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:800;color:{confidence_color};">{data.traversal_analytics.get('total_agents', 0)}</div>
            <div style="font-size:13px;color:#6b7280;margin-top:6px;font-weight:500;">Agents Used</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:800;color:{confidence_color};">{data.traversal_analytics.get('total_documents_visited', 0)}</div>
            <div style="font-size:13px;color:#6b7280;margin-top:6px;font-weight:500;">Docs Visited</div>
        </div>
        <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:800;color:{confidence_color};">{data.traversal_analytics.get('search_effectiveness', 0):.1%}</div>
            <div style="font-size:13px;color:#6b7280;margin-top:6px;font-weight:500;">Effectiveness</div>
        </div>
    </div>

    {f'<div style="margin:20px 0;padding:20px;background:#f9fafb;border-radius:8px;border-left:4px solid {confidence_color};"><h3 style="font-size:18px;font-weight:600;margin:0 0 16px 0;color:#374151;">&#127919; Key Findings</h3>{findings_html}</div>' if findings_html else ''}

    {f'<div style="margin:20px 0;padding:20px;background:#f9fafb;border-radius:8px;border-left:4px solid #3B82F6;"><h3 style="font-size:18px;font-weight:600;margin:0 0 16px 0;color:#374151;">&#128161; Recommendations</h3>{recommendations_html}</div>' if recommendations_html else ''}

    <div style="margin:20px 0;padding:16px;background:#f9fafb;border-radius:8px;border-left:4px solid #6B7280;">
        <h3 style="font-size:16px;font-weight:600;margin:0 0 12px 0;color:#374151;">Technical Details</h3>
        <div style="background:white;padding:12px;border-radius:6px;border:1px solid #e5e7eb;">
            <div><strong>Methodology:</strong> {html.escape(data.search_methodology)}</div>
            <div style="margin-top:8px;"><strong>Generated:</strong> {data.metadata.creation_timestamp}</div>
        </div>
    </div>
</div>
</body>
</html>'''

        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write(html_content)

        return {visualization_uri: VisualizationType.HTML}
