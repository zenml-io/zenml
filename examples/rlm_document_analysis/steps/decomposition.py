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
"""Decomposition step: plans how to partition the corpus for analysis."""

import json
import logging
from typing import Annotated, Any, Dict, List

from utils.llm import _llm_available, llm_call

from zenml import step

logger = logging.getLogger(__name__)

DECOMPOSITION_SYSTEM_PROMPT = """\
You are a research analyst planning how to analyze a large email corpus.

Given a summary of the corpus and a research query, produce a JSON plan
that partitions the emails into chunks for parallel analysis.

Each chunk should focus on a different aspect, time period, or set of
senders relevant to the query. The goal is to divide the work so that
each chunk can be analyzed independently and the results combined.

Respond with a JSON object:
{{
  "chunks": [
    {{
      "start_idx": 0,
      "end_idx": 15,
      "sub_query": "Focused question for this chunk",
      "description": "Why this chunk matters for the overall query"
    }}
  ]
}}

Rules:
- Produce between 2 and {max_chunks} chunks
- Chunks should cover the entire corpus (no gaps)
- start_idx and end_idx are 0-based indices into the email list
- Each sub_query should be a specific, answerable question
- Chunks may overlap slightly if needed for context
"""


def _fallback_decomposition(
    total_emails: int, max_chunks: int, query: str
) -> List[Dict[str, Any]]:
    """Even-split fallback when the LLM is unavailable.

    Args:
        total_emails: Total number of emails in corpus.
        max_chunks: Maximum number of chunks.
        query: The original query (used as sub_query for each chunk).

    Returns:
        List of chunk spec dicts.
    """
    chunk_size = max(1, total_emails // max_chunks)
    chunks = []
    for i in range(max_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total_emails)
        if start >= total_emails:
            break
        chunks.append(
            {
                "start_idx": start,
                "end_idx": end,
                "sub_query": query,
                "description": f"Emails {start}-{end} (even split, chunk {i + 1})",
            }
        )
    # Ensure the last chunk covers remaining emails
    if chunks and chunks[-1]["end_idx"] < total_emails:
        chunks[-1]["end_idx"] = total_emails
    return chunks


@step(enable_cache=False)
def plan_decomposition(
    doc_summary: Dict[str, Any],
    query: str,
    max_chunks: int,
) -> Annotated[List[Dict[str, Any]], "chunk_specs"]:
    """Plan how to partition the email corpus for parallel analysis.

    Uses the LLM to produce intelligent chunk boundaries based on
    the corpus summary and query. Falls back to even splitting when
    no API key is available.

    Args:
        doc_summary: Summary dict from load_documents.
        query: Research question to investigate.
        max_chunks: Maximum number of chunks to produce.

    Returns:
        List of chunk specification dicts.
    """
    total_emails = doc_summary.get("total_emails", 0)
    if total_emails == 0:
        logger.warning("Empty corpus, returning empty chunk list")
        return []

    if not _llm_available():
        logger.info("LLM unavailable, using even-split decomposition")
        return _fallback_decomposition(total_emails, max_chunks, query)

    summary_text = json.dumps(doc_summary, indent=2, default=str)
    system = DECOMPOSITION_SYSTEM_PROMPT.format(max_chunks=max_chunks)
    user_prompt = (
        f"## Corpus Summary\n{summary_text}\n\n"
        f"## Research Query\n{query}\n\n"
        f"Plan the analysis. Total emails: {total_emails}."
    )

    response = llm_call(system, user_prompt, json_mode=True)
    if not response:
        logger.warning("LLM returned empty response, using fallback")
        return _fallback_decomposition(total_emails, max_chunks, query)

    try:
        parsed = json.loads(response)
        chunks = parsed.get("chunks", [])
    except (json.JSONDecodeError, AttributeError):
        logger.warning(
            "Failed to parse decomposition response, using fallback"
        )
        return _fallback_decomposition(total_emails, max_chunks, query)

    # Validate and clamp indices
    validated: List[Dict[str, Any]] = []
    for chunk in chunks[:max_chunks]:
        start = max(0, int(chunk.get("start_idx", 0)))
        end = min(total_emails, int(chunk.get("end_idx", total_emails)))
        if start >= end:
            continue
        validated.append(
            {
                "start_idx": start,
                "end_idx": end,
                "sub_query": chunk.get("sub_query", query),
                "description": chunk.get("description", ""),
            }
        )

    if not validated:
        logger.warning("No valid chunks from LLM, using fallback")
        return _fallback_decomposition(total_emails, max_chunks, query)

    logger.info(
        "Decomposed corpus into %d chunks: %s",
        len(validated),
        [f"{c['start_idx']}-{c['end_idx']}" for c in validated],
    )
    return validated
