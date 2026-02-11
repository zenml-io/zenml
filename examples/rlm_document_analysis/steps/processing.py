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
"""Process chunk step: the self-rolled RLM core.

Each invocation runs a multi-step reasoning loop over a subset of
emails. The loop follows a constrained version of the RLM pattern:

  1. PREVIEW  - Examine the chunk summary
  2. PLAN     - LLM decides which tools to use
  3. SEARCH   - Execute programmatic search tools
  4. EXTRACT  - Pull relevant emails
  5. SUMMARIZE - Produce a structured finding

All steps are logged to a trajectory for full observability.
"""

import json
import logging
import time
from typing import Annotated, Any, Dict, List, Tuple

from utils.llm import _llm_available, llm_call
from utils.tools import (
    TOOL_DESCRIPTIONS,
    count_matches,
    filter_by_date,
    filter_by_recipient,
    filter_by_sender,
    format_email,
    grep_emails,
    preview_chunk,
)

from zenml import log_metadata, step

logger = logging.getLogger(__name__)

SEARCH_PLAN_SYSTEM = """\
You are analyzing a chunk of an email corpus to answer a research question.

You've been shown a preview of the chunk. Now decide what to search for.
You have these tools available:
{tool_descriptions}

Respond with JSON:
{{
  "searches": [
    {{
      "tool": "grep|sender|recipient|date|count",
      "args": {{"pattern": "..."}} or {{"sender": "..."}} or \
{{"recipient": "..."}} or {{"start": "...", "end": "..."}} or {{"pattern": "..."}},
      "reason": "Why this search helps answer the question"
    }}
  ]
}}

Produce 1-4 searches that would help answer the sub-query.
"""

SUMMARIZE_SYSTEM = """\
You are a research analyst summarizing findings from an email corpus search.

Given the original query, the search results, and the relevant emails,
produce a clear, evidence-based finding.

Respond with JSON:
{{
  "finding": "Your main finding in 2-4 sentences",
  "confidence": "high|medium|low",
  "key_evidence": [
    "Brief description of supporting email or fact"
  ],
  "relevant_email_indices": [0, 3, 7]
}}

Be specific. Cite dates, names, and amounts when available.
If the chunk doesn't contain relevant information, say so clearly.
"""


def _execute_search(
    emails: List[Dict[str, Any]], search: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a single search tool call and return results.

    Args:
        emails: The chunk of emails to search.
        search: Search spec with 'tool' and 'args' keys.

    Returns:
        Dict with tool name, args, match count, and matched emails.
    """
    tool = search.get("tool", "")
    args = search.get("args", {})

    if tool == "grep":
        matches = grep_emails(emails, args.get("pattern", ""))
    elif tool == "sender":
        matches = filter_by_sender(emails, args.get("sender", ""))
    elif tool == "recipient":
        matches = filter_by_recipient(emails, args.get("recipient", ""))
    elif tool == "date":
        matches = filter_by_date(
            emails, args.get("start", ""), args.get("end", "")
        )
    elif tool == "count":
        n = count_matches(emails, args.get("pattern", ""))
        return {
            "tool": tool,
            "args": args,
            "match_count": n,
            "matches": [],
        }
    else:
        return {
            "tool": tool,
            "args": args,
            "match_count": 0,
            "matches": [],
            "error": f"Unknown tool: {tool}",
        }

    return {
        "tool": tool,
        "args": args,
        "match_count": len(matches),
        "matches": matches,
    }


def _fallback_process(
    chunk_emails: List[Dict[str, Any]],
    sub_query: str,
) -> Dict[str, Any]:
    """Keyword-based fallback when LLM is unavailable.

    Args:
        chunk_emails: Emails in this chunk.
        sub_query: The sub-query for this chunk.

    Returns:
        Finding dict with keyword-matched results.
    """
    keywords = sub_query.lower().split()
    matches = []
    for e in chunk_emails:
        text = (e.get("body", "") + " " + e.get("subject", "")).lower()
        if any(kw in text for kw in keywords):
            matches.append(e)

    return {
        "finding": (
            f"Keyword search found {len(matches)} emails matching "
            f"query terms in a chunk of {len(chunk_emails)} emails."
        ),
        "confidence": "low",
        "key_evidence": [
            f"[{m.get('date', 'N/A')}] {m.get('subject', '(no subject)')}"
            for m in matches[:5]
        ],
        "relevant_emails": matches[:10],
        "mode": "keyword_fallback",
    }


@step(enable_cache=False)
def process_chunk(
    documents: List[Dict[str, Any]],
    chunk_spec: Dict[str, Any],
    query: str,
    max_iterations: int,
) -> Tuple[
    Annotated[Dict[str, Any], "chunk_result"],
    Annotated[List[Dict[str, Any]], "trajectory"],
]:
    """Analyze a chunk of emails using the self-rolled RLM pattern.

    Runs a multi-step reasoning loop: preview the chunk, plan searches,
    execute them, extract relevant emails, and summarize findings.
    Every action is logged to a trajectory artifact.

    Args:
        documents: Full email list (sliced by chunk_spec indices).
        chunk_spec: Dict with start_idx, end_idx, sub_query, description.
        query: The overall research query.
        max_iterations: Max LLM calls per chunk.

    Returns:
        Tuple of (finding dict, trajectory list).
    """
    start_time = time.time()
    start_idx = chunk_spec.get("start_idx", 0)
    end_idx = chunk_spec.get("end_idx", len(documents))
    sub_query = chunk_spec.get("sub_query", query)
    description = chunk_spec.get("description", "")

    chunk_emails = documents[start_idx:end_idx]
    trajectory: List[Dict[str, Any]] = []
    llm_calls = 0

    logger.info(
        "Processing chunk [%d:%d] (%d emails) — %s",
        start_idx,
        end_idx,
        len(chunk_emails),
        description,
    )

    # --- Step 1: PREVIEW ---
    preview_text = preview_chunk(chunk_emails, n=5)
    trajectory.append(
        {
            "step": "preview",
            "action": f"Examined {len(chunk_emails)} emails",
            "output": preview_text[:500],
        }
    )

    if not _llm_available():
        result = _fallback_process(chunk_emails, sub_query)
        trajectory.append(
            {
                "step": "fallback",
                "action": "Used keyword matching (no API key)",
            }
        )
        log_metadata(
            metadata={
                "chunk_range": f"{start_idx}-{end_idx}",
                "chunk_size": len(chunk_emails),
                "llm_calls": 0,
                "mode": "fallback",
                "duration_s": round(time.time() - start_time, 2),
            }
        )
        return result, trajectory

    # --- Step 2: PLAN ---
    tool_desc = "\n".join(f"  - {v}" for v in TOOL_DESCRIPTIONS.values())
    plan_prompt = (
        f"## Sub-query\n{sub_query}\n\n"
        f"## Chunk Preview\n{preview_text}\n\n"
        f"What searches should we run to answer this question?"
    )
    plan_response = llm_call(
        SEARCH_PLAN_SYSTEM.format(tool_descriptions=tool_desc),
        plan_prompt,
        json_mode=True,
    )
    llm_calls += 1

    searches: List[Dict[str, Any]] = []
    if plan_response:
        try:
            plan_data = json.loads(plan_response)
            searches = plan_data.get("searches", [])[:4]
        except json.JSONDecodeError:
            logger.warning("Failed to parse search plan")

    trajectory.append(
        {
            "step": "plan",
            "action": f"Planned {len(searches)} searches",
            "searches": [
                {"tool": s.get("tool"), "reason": s.get("reason", "")}
                for s in searches
            ],
        }
    )

    # --- Step 3: SEARCH ---
    all_matches: List[Dict[str, Any]] = []
    search_results_text: List[str] = []

    for search in searches:
        result = _execute_search(chunk_emails, search)
        trajectory.append(
            {
                "step": "search",
                "tool": result["tool"],
                "args": result.get("args", {}),
                "match_count": result["match_count"],
            }
        )
        search_results_text.append(
            f"Tool: {result['tool']}({result.get('args', {})}) "
            f"→ {result['match_count']} matches"
        )
        for m in result.get("matches", []):
            if m not in all_matches:
                all_matches.append(m)

    trajectory.append(
        {
            "step": "extract",
            "action": f"Found {len(all_matches)} unique matching emails",
        }
    )

    # --- Step 4: SUMMARIZE ---
    # Cap the evidence text to stay within context limits
    evidence_texts: List[str] = []
    char_budget = 8000
    for m in all_matches:
        formatted = format_email(m, max_body=400)
        if char_budget - len(formatted) < 0:
            break
        evidence_texts.append(formatted)
        char_budget -= len(formatted)

    summarize_prompt = (
        f"## Research Query\n{query}\n\n"
        f"## Sub-query for This Chunk\n{sub_query}\n\n"
        f"## Search Results\n" + "\n".join(search_results_text) + "\n\n"
        f"## Relevant Emails ({len(evidence_texts)} shown)\n"
        + "\n---\n".join(evidence_texts)
    )
    summary_response = llm_call(
        SUMMARIZE_SYSTEM, summarize_prompt, json_mode=True
    )
    llm_calls += 1

    finding: Dict[str, Any] = {}
    if summary_response:
        try:
            finding = json.loads(summary_response)
        except json.JSONDecodeError:
            finding = {"finding": summary_response, "confidence": "low"}

    if not finding.get("finding"):
        finding = {
            "finding": (
                f"Searched {len(chunk_emails)} emails with "
                f"{len(searches)} queries. Found {len(all_matches)} matches."
            ),
            "confidence": "low",
            "key_evidence": [
                f"[{m.get('date', '')}] {m.get('subject', '')}"
                for m in all_matches[:5]
            ],
        }

    # Attach chunk metadata to the finding
    finding["chunk_range"] = f"{start_idx}-{end_idx}"
    finding["chunk_description"] = description
    finding["emails_searched"] = len(chunk_emails)
    finding["matches_found"] = len(all_matches)

    trajectory.append(
        {
            "step": "summarize",
            "finding_preview": str(finding.get("finding", ""))[:300],
            "confidence": finding.get("confidence", "unknown"),
        }
    )

    duration = round(time.time() - start_time, 2)
    log_metadata(
        metadata={
            "chunk_range": f"{start_idx}-{end_idx}",
            "chunk_size": len(chunk_emails),
            "llm_calls": llm_calls,
            "matches_found": len(all_matches),
            "duration_s": duration,
        }
    )

    logger.info(
        "Chunk [%d:%d] done in %.1fs: %d matches, %d LLM calls",
        start_idx,
        end_idx,
        duration,
        len(all_matches),
        llm_calls,
    )

    return finding, trajectory
