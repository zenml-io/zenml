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

REPORT_CSS = """\
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', \
Roboto, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; \
color: #1a1a1a; background: #fafafa; }
h1 { color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 0.3em; }
h2 { color: #1e40af; margin-top: 1.5em; }
.finding-card { background: white; border: 1px solid #e5e7eb; \
border-radius: 8px; padding: 1.2em; margin: 1em 0; \
box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.finding-card h3 { margin-top: 0; color: #374151; }
.confidence { display: inline-block; padding: 2px 10px; border-radius: 12px; \
font-size: 0.85em; font-weight: 600; }
.confidence-high { background: #d1fae5; color: #065f46; }
.confidence-medium { background: #fef3c7; color: #92400e; }
.confidence-low { background: #fee2e2; color: #991b1b; }
.evidence { background: #f9fafb; border-left: 3px solid #2563eb; \
padding: 0.8em 1em; margin: 0.5em 0; font-size: 0.9em; }
.meta { color: #6b7280; font-size: 0.85em; }
.summary-box { background: #eff6ff; border: 1px solid #bfdbfe; \
border-radius: 8px; padding: 1.2em; margin: 1em 0; }
"""


def _build_report(
    query: str,
    synthesis: Dict[str, Any],
    chunk_findings: List[Dict[str, Any]],
) -> str:
    """Build an HTML report from synthesis and chunk findings.

    Args:
        query: The original research query.
        synthesis: Combined synthesis dict from LLM.
        chunk_findings: List of per-chunk finding dicts.

    Returns:
        HTML string.
    """
    q = html.escape(query)
    summary = html.escape(
        str(synthesis.get("summary", "No summary available."))
    )
    confidence = synthesis.get("confidence", "unknown")
    conf_class = (
        f"confidence-{confidence}"
        if confidence in ("high", "medium", "low")
        else ""
    )

    key_findings_html = ""
    for kf in synthesis.get("key_findings", []):
        key_findings_html += (
            f'<div class="evidence">{html.escape(str(kf))}</div>\n'
        )

    gaps = html.escape(str(synthesis.get("evidence_gaps", "")))

    chunk_cards = ""
    for i, cf in enumerate(chunk_findings):
        finding_text = html.escape(str(cf.get("finding", "No finding.")))
        chunk_range = html.escape(str(cf.get("chunk_range", "N/A")))
        desc = html.escape(str(cf.get("chunk_description", "")))
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
            evidence_items += (
                f'<div class="evidence">{html.escape(str(ev))}</div>\n'
            )

        chunk_cards += f"""
        <div class="finding-card">
          <h3>Chunk {i + 1}: Emails [{chunk_range}]</h3>
          <p class="meta">{desc}</p>
          <p class="meta">Searched {emails_searched} emails, \
found {matches_found} matches</p>
          <span class="confidence {cf_class}">{cf_confidence}</span>
          <p>{finding_text}</p>
          {evidence_items}
        </div>
        """

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>RLM Analysis Report</title>
<style>{REPORT_CSS}</style></head>
<body>
<h1>RLM Document Analysis Report</h1>
<p class="meta">Query: <strong>{q}</strong></p>
<p class="meta">Analyzed {len(chunk_findings)} chunks</p>

<div class="summary-box">
  <h2>Synthesis</h2>
  <span class="confidence {conf_class}">{confidence}</span>
  <p>{summary}</p>
</div>

<h2>Key Findings</h2>
{key_findings_html}

{f"<h2>Evidence Gaps</h2><p>{gaps}</p>" if gaps else ""}

<h2>Per-Chunk Analysis</h2>
{chunk_cards}
</body></html>"""


@step
def aggregate_results(
    chunk_results: List[Dict[str, Any]],
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

    report_html = _build_report(query, synthesis, chunk_results)

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
