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

Each invocation runs an iterative reasoning loop over a subset of
emails, bounded by a configurable LLM-call budget (max_iterations).

The loop follows a constrained version of the RLM pattern:

  1. PREVIEW   - Examine the chunk summary (no LLM call)
  2. PLAN      - LLM decides which tools to use (1 LLM call)
  3. SEARCH    - Execute programmatic search tools (0 LLM calls)
  4. REFLECT   - LLM evaluates findings so far: sufficient, or
                 refine the search strategy? (1 LLM call)
     └─ If not sufficient, loop back to PLAN with refined strategy
  5. SUMMARIZE - Produce a final structured finding (1 LLM call)

Each plan+reflect iteration costs 2 LLM calls; the final summarize
costs 1. So max_iterations=6 allows up to 2 full search rounds plus
the final synthesis.

All steps are logged to a trajectory for full observability.
"""

import json
import logging
import time
from typing import Annotated, Any, Dict, List, Tuple

from utils.llm import llm_available, llm_call
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

REFLECT_SYSTEM = """\
You are a research analyst reviewing search results from an email corpus.

You ran some searches and found partial results. Now decide: do you have
enough evidence to answer the question, or should you search differently?

Respond with JSON:
{{
  "sufficient": true or false,
  "reasoning": "Why the evidence is or isn't enough",
  "next_searches": [
    {{
      "tool": "grep|sender|recipient|date|count",
      "args": {{"pattern": "..."}} or {{"sender": "..."}} etc.,
      "reason": "What this new search would reveal"
    }}
  ]
}}

If sufficient=true, next_searches should be empty.
If sufficient=false, suggest 1-3 NEW searches (different from previous ones).
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
    """Analyze a chunk of emails using an iterative RLM reasoning loop.

    Runs a bounded iterative loop: preview → plan → search → reflect.
    The reflect step evaluates whether enough evidence has been found;
    if not, it feeds back to the plan step with guidance on what to
    search next. The loop stops when the LLM judges evidence sufficient
    or the LLM-call budget (max_iterations) is exhausted. A final
    summarize step synthesizes all gathered evidence.

    Each plan+reflect iteration costs 2 LLM calls; the final summarize
    costs 1. So max_iterations=6 allows up to 2 full search rounds
    plus the final synthesis.

    Args:
        documents: Full email list (sliced by chunk_spec indices).
        chunk_spec: Dict with start_idx, end_idx, sub_query, description.
        query: The overall research query.
        max_iterations: Max LLM calls for this chunk. Controls analysis
            depth: higher values allow more search-reflect iterations.

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

    if not llm_available():
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

    # --- Iterative RLM loop: PLAN → SEARCH → REFLECT → (repeat or stop) ---
    tool_desc = "\n".join(f"  - {v}" for v in TOOL_DESCRIPTIONS.values())
    all_matches: List[Dict[str, Any]] = []
    search_results_text: List[str] = []
    seen_ids: set = set()
    iteration = 0
    prior_search_summary = ""
    reflect_feedback = ""

    while llm_calls < max_iterations - 1:
        # Reserve 1 LLM call for final SUMMARIZE
        iteration += 1

        # --- PLAN ---
        if iteration == 1:
            plan_prompt = (
                f"## Sub-query\n{sub_query}\n\n"
                f"## Chunk Preview\n{preview_text}\n\n"
                f"What searches should we run to answer this question?"
            )
        else:
            plan_prompt = (
                f"## Sub-query\n{sub_query}\n\n"
                f"## Chunk Preview\n{preview_text}\n\n"
                f"## Previous Searches\n{prior_search_summary}\n\n"
                f"## Reflection Feedback\n{reflect_feedback}\n\n"
                f"Plan NEW searches (different from those already run)."
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
                logger.warning("Failed to parse search plan (iteration %d)", iteration)

        trajectory.append(
            {
                "step": "plan",
                "iteration": iteration,
                "action": f"Planned {len(searches)} searches",
                "searches": [
                    {"tool": s.get("tool"), "reason": s.get("reason", "")}
                    for s in searches
                ],
            }
        )

        if not searches:
            logger.info("No searches planned in iteration %d, stopping", iteration)
            break

        # --- SEARCH ---
        iteration_matches = 0
        for search in searches:
            result = _execute_search(chunk_emails, search)
            trajectory.append(
                {
                    "step": "search",
                    "iteration": iteration,
                    "tool": result["tool"],
                    "args": result.get("args", {}),
                    "match_count": result["match_count"],
                }
            )
            search_results_text.append(
                f"[iter {iteration}] {result['tool']}({result.get('args', {})}) "
                f"→ {result['match_count']} matches"
            )
            for m in result.get("matches", []):
                m_id = m.get("id", id(m))
                if m_id not in seen_ids:
                    seen_ids.add(m_id)
                    all_matches.append(m)
                    iteration_matches += 1

        trajectory.append(
            {
                "step": "extract",
                "iteration": iteration,
                "new_matches": iteration_matches,
                "total_matches": len(all_matches),
            }
        )

        prior_search_summary = "\n".join(search_results_text)

        # Check if we have budget for a REFLECT call (need >=2 remaining:
        # 1 for reflect + 1 for final summarize)
        if llm_calls >= max_iterations - 1:
            logger.info("LLM budget reached after search, skipping reflect")
            break

        # --- REFLECT ---
        reflect_prompt = (
            f"## Sub-query\n{sub_query}\n\n"
            f"## Searches So Far\n{prior_search_summary}\n\n"
            f"## Total Unique Matches: {len(all_matches)}\n\n"
            f"Do we have enough evidence to answer the question, or should "
            f"we try different searches?"
        )
        reflect_response = llm_call(
            REFLECT_SYSTEM, reflect_prompt, json_mode=True
        )
        llm_calls += 1

        sufficient = True
        reflect_feedback = ""
        if reflect_response:
            try:
                reflect_data = json.loads(reflect_response)
                sufficient = reflect_data.get("sufficient", True)
                reflect_feedback = reflect_data.get("reasoning", "")
            except json.JSONDecodeError:
                logger.warning("Failed to parse reflect response, stopping loop")

        trajectory.append(
            {
                "step": "reflect",
                "iteration": iteration,
                "sufficient": sufficient,
                "reasoning": reflect_feedback[:300],
            }
        )

        if sufficient:
            logger.info(
                "Reflection says sufficient after iteration %d", iteration
            )
            break

        logger.info(
            "Iteration %d: %d new matches, reflecting: %s",
            iteration,
            iteration_matches,
            reflect_feedback[:100],
        )

    # --- SUMMARIZE (final LLM call) ---
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
        f"## Search Results ({iteration} iteration(s))\n"
        + "\n".join(search_results_text) + "\n\n"
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
                f"Searched {len(chunk_emails)} emails over "
                f"{iteration} iteration(s) with "
                f"{len(search_results_text)} tool calls. "
                f"Found {len(all_matches)} matches."
            ),
            "confidence": "low",
            "key_evidence": [
                f"[{m.get('date', '')}] {m.get('subject', '')}"
                for m in all_matches[:5]
            ],
        }

    finding["chunk_range"] = f"{start_idx}-{end_idx}"
    finding["chunk_description"] = description
    finding["emails_searched"] = len(chunk_emails)
    finding["matches_found"] = len(all_matches)
    finding["iterations"] = iteration
    finding["llm_calls"] = llm_calls

    trajectory.append(
        {
            "step": "summarize",
            "finding_preview": str(finding.get("finding", ""))[:300],
            "confidence": finding.get("confidence", "unknown"),
            "total_iterations": iteration,
            "total_llm_calls": llm_calls,
        }
    )

    duration = round(time.time() - start_time, 2)
    log_metadata(
        metadata={
            "chunk_range": f"{start_idx}-{end_idx}",
            "chunk_size": len(chunk_emails),
            "llm_calls": llm_calls,
            "iterations": iteration,
            "matches_found": len(all_matches),
            "duration_s": duration,
        }
    )

    logger.info(
        "Chunk [%d:%d] done in %.1fs: %d matches, %d iterations, %d LLM calls",
        start_idx,
        end_idx,
        duration,
        len(all_matches),
        iteration,
        llm_calls,
    )

    return finding, trajectory
