# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Aggregation step: synthesizes findings from all chunks into a report."""

import html
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Dict, List, Tuple

from utils.llm import llm_available, llm_call

from zenml import step
from zenml.types import HTMLString

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM = """\
You are a senior research analyst synthesizing findings from multiple
independent analyses of an email corpus.

Each chunk analysis produced a finding about a subset of the corpus.
Combine these into a single coherent answer to the original query.

Respond with JSON:
{
  "summary": "3-5 sentence synthesis answering the original query",
  "key_findings": [
    "Numbered finding with specific evidence"
  ],
  "confidence": "high|medium|low",
  "evidence_gaps": "What additional analysis might strengthen these findings"
}

Be specific. Reference dates, names, and amounts. Note contradictions
or gaps between chunk findings.
"""


# --- Asset loading (mirrors hierarchical example pattern) ---


@lru_cache(maxsize=8)
def _load_text_asset(rel_path: str) -> str:
    """Load a UTF-8 text asset with local + Docker + relative fallbacks.

    Args:
        rel_path: Relative path from example root (e.g., "data/report.css").

    Returns:
        File contents as string, or empty string if not found.
    """
    search_paths = [
        Path(__file__).parent.parent / rel_path,
        Path("/app") / rel_path,
        Path(rel_path),
    ]
    for p in search_paths:
        try:
            return p.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            continue
    logger.warning("Asset not found: %s", rel_path)
    return ""


def _get_report_css() -> str:
    """Return CSS styles for the HTML report (loaded from external file)."""
    return _load_text_asset("data/report.css")


def _get_report_template() -> str:
    """Return the HTML template for the report (loaded from external file)."""
    return _load_text_asset("data/report_template.html")


# --- Report building ---


def _escape(value: Any) -> str:
    """HTML-escape any value to a string."""
    return html.escape(str(value))


def _render_trajectory_block(trajectory: List[Dict[str, Any]]) -> str:
    """Render a collapsible trajectory section for a chunk card.

    Args:
        trajectory: List of trajectory event dicts.

    Returns:
        HTML string for a <details> block, or empty string if no events.
    """
    if not trajectory:
        return ""
    traj_json = html.escape(json.dumps(trajectory, indent=2, default=str))
    return (
        f'<details class="trajectory-details">'
        f"<summary>Trajectory ({len(trajectory)} events)</summary>"
        f'<pre class="trajectory-pre">{traj_json}</pre>'
        f"</details>"
    )


def _build_chunk_cards(
    chunk_findings: List[Dict[str, Any]],
    chunk_trajectories: List[List[Dict[str, Any]]],
) -> str:
    """Build HTML cards for each chunk with findings and trajectories.

    Args:
        chunk_findings: List of per-chunk finding dicts.
        chunk_trajectories: List of trajectory lists per chunk.

    Returns:
        Combined HTML string of all chunk cards.
    """
    cards = ""
    for i, cf in enumerate(chunk_findings):
        finding_text = _escape(cf.get("finding", "No finding."))
        chunk_range = _escape(cf.get("chunk_range", "N/A"))
        desc = _escape(cf.get("chunk_description", ""))
        cf_confidence = cf.get("confidence", "unknown")
        cf_class = (
            f"confidence-{cf_confidence}"
            if cf_confidence in ("high", "medium", "low")
            else ""
        )
        emails_searched = cf.get("emails_searched", "?")
        matches_found = cf.get("matches_found", "?")

        evidence_items = ""
        for ev in cf.get("key_evidence", []):
            evidence_items += f'<div class="evidence">{_escape(ev)}</div>\n'

        traj = chunk_trajectories[i] if i < len(chunk_trajectories) else []
        trajectory_html = _render_trajectory_block(traj)

        cards += (
            f'<div class="finding-card">'
            f"<h3>Chunk {i + 1}: Emails [{chunk_range}]</h3>"
            f'<p class="meta">{desc}</p>'
            f'<p class="meta">Searched {emails_searched} emails, '
            f"found {matches_found} matches</p>"
            f'<span class="confidence {cf_class}">{cf_confidence}</span>'
            f"<p>{finding_text}</p>"
            f"{evidence_items}"
            f"{trajectory_html}"
            f"</div>\n"
        )
    return cards


def _build_report(
    query: str,
    synthesis: Dict[str, Any],
    chunk_findings: List[Dict[str, Any]],
    chunk_trajectories: List[List[Dict[str, Any]]],
) -> str:
    """Build an HTML report from synthesis and chunk findings.

    Loads external CSS and HTML template, then renders the report.
    Falls back to a minimal inline report if template is missing.

    Args:
        query: The original research query.
        synthesis: Combined synthesis dict from LLM.
        chunk_findings: List of per-chunk finding dicts.
        chunk_trajectories: List of trajectory lists per chunk.

    Returns:
        HTML string.
    """
    css = _get_report_css()
    template = _get_report_template()

    # Pre-render sub-sections
    query_safe = _escape(query)
    summary_safe = _escape(synthesis.get("summary", "No summary available."))
    confidence = synthesis.get("confidence", "unknown")
    confidence_class = (
        f"confidence-{confidence}"
        if confidence in ("high", "medium", "low")
        else ""
    )

    key_findings_html = ""
    for kf in synthesis.get("key_findings", []):
        key_findings_html += f'<div class="evidence">{_escape(kf)}</div>\n'

    gaps = str(synthesis.get("evidence_gaps", ""))
    evidence_gaps_html = (
        f'<div class="gaps-section"><h2>Evidence Gaps</h2>'
        f"<p>{_escape(gaps)}</p></div>"
        if gaps
        else ""
    )

    chunk_cards_html = _build_chunk_cards(chunk_findings, chunk_trajectories)

    if not template:
        logger.warning(
            "Report template not found; rendering minimal fallback."
        )
        return (
            f"<html><body><h1>RLM Analysis Report</h1>"
            f"<p>Query: {query_safe}</p>"
            f"<p>{summary_safe}</p>"
            f"{chunk_cards_html}</body></html>"
        )

    try:
        return template.format(
            css=css,
            query_safe=query_safe,
            chunk_count=len(chunk_findings),
            confidence_safe=_escape(confidence),
            confidence_class=confidence_class,
            summary_safe=summary_safe,
            key_findings_html=key_findings_html,
            evidence_gaps_html=evidence_gaps_html,
            chunk_cards_html=chunk_cards_html,
        )
    except (KeyError, ValueError) as exc:
        logger.warning("Template rendering failed: %s", exc)
        return (
            f"<html><body><h1>RLM Analysis Report</h1>"
            f"<p>Query: {query_safe}</p>"
            f"<p>{summary_safe}</p>"
            f"{chunk_cards_html}</body></html>"
        )


# --- Step ---


@step
def aggregate_results(
    chunk_results: List[Dict[str, Any]],
    chunk_trajectories: List[List[Dict[str, Any]]],
    query: str,
) -> Tuple[
    Annotated[Dict[str, Any], "analysis_results"],
    Annotated[HTMLString, "report"],
]:
    """Combine findings from all chunk analyses into a final report.

    Uses the LLM to synthesize per-chunk findings into a coherent
    answer. Falls back to concatenation when no API key is set.
    Produces both a structured result dict and an HTML report artifact.

    Args:
        chunk_results: List of finding dicts from process_chunk steps.
        chunk_trajectories: List of trajectory lists from process_chunk steps.
        query: The original research query.

    Returns:
        Tuple of (structured results dict, HTML report).
    """
    logger.info("Aggregating results from %d chunks", len(chunk_results))

    if not chunk_results:
        empty_result: Dict[str, Any] = {
            "summary": "No chunks were analyzed.",
            "key_findings": [],
            "confidence": "low",
            "chunk_count": 0,
        }
        return empty_result, HTMLString(
            "<html><body><p>No results.</p></body></html>"
        )

    # Build synthesis
    synthesis: Dict[str, Any]
    if llm_available():
        findings_text = json.dumps(
            [
                {
                    "chunk": cf.get("chunk_range", "?"),
                    "finding": cf.get("finding", ""),
                    "confidence": cf.get("confidence", ""),
                    "key_evidence": cf.get("key_evidence", []),
                }
                for cf in chunk_results
            ],
            indent=2,
        )
        synthesis_prompt = (
            f"## Original Query\n{query}\n\n"
            f"## Chunk Findings\n{findings_text}\n\n"
            f"Synthesize these into a final answer."
        )
        response = llm_call(SYNTHESIS_SYSTEM, synthesis_prompt, json_mode=True)
        if response:
            try:
                synthesis = json.loads(response)
            except json.JSONDecodeError:
                synthesis = {
                    "summary": response,
                    "confidence": "low",
                    "key_findings": [],
                }
        else:
            synthesis = _fallback_synthesis(chunk_results)
    else:
        synthesis = _fallback_synthesis(chunk_results)

    synthesis["chunk_count"] = len(chunk_results)
    synthesis["query"] = query

    # Pad trajectories if length mismatch (defensive)
    while len(chunk_trajectories) < len(chunk_results):
        chunk_trajectories.append([])

    report_html = _build_report(
        query, synthesis, chunk_results, chunk_trajectories
    )

    logger.info(
        "Analysis complete: %d chunks, confidence=%s",
        len(chunk_results),
        synthesis.get("confidence", "unknown"),
    )

    return synthesis, HTMLString(report_html)


def _fallback_synthesis(
    chunk_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Concatenate chunk findings without LLM synthesis.

    Args:
        chunk_results: List of finding dicts.

    Returns:
        Combined synthesis dict.
    """
    all_findings = [
        str(cf.get("finding", "")) for cf in chunk_results if cf.get("finding")
    ]
    all_evidence: List[str] = []
    for cf in chunk_results:
        all_evidence.extend(str(e) for e in cf.get("key_evidence", []))
    return {
        "summary": " | ".join(all_findings)
        if all_findings
        else "No findings.",
        "key_findings": all_evidence[:10],
        "confidence": "low",
        "evidence_gaps": "LLM synthesis unavailable; findings concatenated.",
    }
