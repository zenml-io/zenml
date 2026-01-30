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
"""Search steps for hierarchical document traversal."""

import html
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, ModelHTTPError

from zenml import step
from zenml.types import HTMLString

logger = logging.getLogger(__name__)

# --- Configuration ---

DEFAULT_MODEL = "openai:gpt-5-nano"
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL)

# Maximum characters for answer text (0 = unlimited)
# Set via MAX_ANSWER_CHARS env var to override
DEFAULT_MAX_ANSWER_CHARS = 10000
MAX_ANSWER_CHARS = int(
    os.getenv("MAX_ANSWER_CHARS", str(DEFAULT_MAX_ANSWER_CHARS))
)

# Lazy-initialized agent (avoid import-time failure when API key is missing)
_traversal_agent: Optional[Any] = None


def _get_traversal_agent() -> Any:
    """Lazily initialize the Pydantic AI agent."""
    global _traversal_agent
    if _traversal_agent is None:
        from pydantic_ai import Agent

        _traversal_agent = Agent(
            LLM_MODEL,
            output_type=TraversalDecision,
            system_prompt="""You are a document search agent. Given a query and document content,
            decide whether this document answers the query or if you should explore related documents.

            If the document answers the query: set has_answer=True and provide the answer.
            If not: set has_answer=False and list document IDs to explore in traverse_to.

            IMPORTANT: You MUST only output document IDs that appear in the provided 'Related documents'
            list. Do not invent or hallucinate document IDs. If no related documents are relevant,
            return an empty traverse_to list.""",
        )
    return _traversal_agent


def _llm_available() -> bool:
    """Check if LLM calls should be attempted (API key present).

    Note: This checks for OPENAI_API_KEY regardless of LLM_MODEL setting.
    The example assumes OpenAI-compatible models. For other providers,
    modify this check or set OPENAI_API_KEY to a valid API key for your
    provider if it uses the OpenAI-compatible API format.
    """
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


# Module-level flag to log "LLM unavailable" only once
_llm_unavailable_logged = False


def _is_transient_error(exc: BaseException) -> bool:
    """Return True if the exception is likely transient (retryable)."""
    if isinstance(exc, ModelHTTPError):
        # Retry on rate limits and server errors
        return exc.status_code in (429, 500, 502, 503, 504)
    # Network-level errors are also transient
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    return False


def _run_agent_with_retry(
    agent: Any,
    prompt: str,
    *,
    max_retries: int = 3,
    initial_backoff_s: float = 0.5,
    max_backoff_s: float = 8.0,
) -> Any:
    """Run agent.run_sync(prompt) with exponential backoff on transient errors."""
    last_exception: Optional[BaseException] = None

    for attempt in range(max_retries + 1):
        try:
            return agent.run_sync(prompt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except (
            ModelHTTPError,
            ModelAPIError,
            AgentRunError,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as e:
            last_exception = e
            # Check if this is a transient error (or wrapped transient error)
            is_transient = _is_transient_error(e)
            if hasattr(e, "__cause__") and e.__cause__:
                is_transient = is_transient or _is_transient_error(e.__cause__)
            if not is_transient or attempt == max_retries:
                raise
            # Exponential backoff with jitter
            delay = min(max_backoff_s, initial_backoff_s * (2**attempt))
            delay *= random.uniform(0.8, 1.2)
            logger.info(
                f"Transient error (attempt {attempt + 1}), retrying in {delay:.1f}s: {e}"
            )
            time.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly")


def _truncate_text(text: Optional[str], max_chars: int = 2000) -> str:
    """Return text truncated to max_chars (safe for None).

    Args:
        text: Text to truncate.
        max_chars: Maximum characters. If <= 0, no truncation is applied.

    Returns:
        Truncated text with '...' suffix if truncated, or original text.
    """
    if not text:
        return ""
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _validate_traverse_to(
    traverse_to: List[str],
    *,
    related: List[str],
    docs: Dict[str, Any],
) -> List[str]:
    """Filter traversal targets to IDs that are both related AND exist in the graph."""
    # Only allow IDs that are BOTH in the related list AND exist in the document graph
    allowed = set(related) & set(docs.keys())
    seen: set[str] = set()
    result: List[str] = []
    for doc_id in traverse_to:
        if (
            doc_id
            and isinstance(doc_id, str)
            and doc_id in allowed
            and doc_id not in seen
        ):
            result.append(doc_id)
            seen.add(doc_id)
    return result


# --- Data loading ---


def _load_documents() -> Dict[str, Any]:
    """Load document graph from JSON file.

    Tries multiple paths and handles various error conditions gracefully,
    continuing to fallback paths on failure.
    """
    search_paths = [
        Path(__file__).parent.parent / "data" / "doc_graph.json",
        Path("/app/data/doc_graph.json"),  # Docker container path
        Path("data/doc_graph.json"),  # Relative fallback
    ]
    for doc_path in search_paths:
        if not doc_path.exists():
            continue
        raw: str = ""
        try:
            raw = doc_path.read_text(encoding="utf-8")
        except OSError as e:
            # Handle permission errors, transient FS issues, etc.
            logger.warning(f"Could not read {doc_path}: {e}")
            continue

        try:
            data: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as e:
            # Provide helpful context for debugging malformed JSON
            lines = raw.splitlines()
            error_line = lines[e.lineno - 1] if e.lineno <= len(lines) else ""
            # Truncate long lines for readability
            if len(error_line) > 120:
                error_line = error_line[:120] + "..."
            logger.error(
                f"Invalid JSON in {doc_path} at line {e.lineno}, "
                f"column {e.colno}: {e.msg}\n"
                f"  Line content: {error_line}"
            )
            continue

        # Validate schema: "documents" key must exist and be a dict
        try:
            docs = data["documents"]
            if not isinstance(docs, dict):
                raise TypeError("'documents' must be a JSON object (dict)")
            return docs
        except (KeyError, TypeError) as e:
            logger.warning(f"Invalid schema in {doc_path}: {e}")
            continue

    logger.warning(
        f"Document graph not found or invalid in any of: {search_paths}"
    )
    return {}


# --- Pydantic AI Agent for traversal decisions ---


class TraversalDecision(BaseModel):
    """Agent's decision: answer the query or traverse deeper."""

    has_answer: bool
    answer: str = ""
    traverse_to: List[str] = Field(default_factory=list)
    reasoning: str = ""


# --- Steps ---


@step
def detect_intent(query: str) -> Annotated[str, "search_type"]:
    """Classify as 'simple' or 'deep' search."""
    simple = ["what is", "define", "basics of"]
    deep = ["how", "relate", "compare", "between", "connection"]
    q = query.lower()
    return (
        "simple"
        if any(s in q for s in simple) and not any(d in q for d in deep)
        else "deep"
    )


@step
def simple_search(
    query: str, search_type: str
) -> Annotated[Dict[str, Any], "search_results"]:
    """Fast keyword search for simple queries."""
    _ = search_type  # Creates DAG edge from detect_intent
    docs = _load_documents()
    words = set(query.lower().split())
    if not words:
        return {
            "query": query,
            "type": "simple",
            "results": [],
            "agents_used": 0,
        }
    results = []
    for doc_id, doc in docs.items():
        text = f"{doc.get('title', '')} {doc.get('content', '')}".lower()
        score = sum(1 for w in words if w in text) / len(words)
        if score > 0:
            results.append(
                {"doc_id": doc_id, "title": doc.get("title"), "score": score}
            )
    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "query": query,
        "type": "simple",
        "results": results[:5],
        "agents_used": 0,
    }


@step
def plan_search(
    query: str, max_agents: int, search_type: str
) -> Annotated[List[str], "seed_nodes"]:
    """Find starting documents for deep search agents."""
    _ = search_type  # Creates DAG edge from detect_intent
    docs = _load_documents()
    words = set(query.lower().split())
    if not words:
        return []
    scored = []
    for doc_id, doc in docs.items():
        text = f"{doc.get('title', '')} {doc.get('content', '')}".lower()
        score = sum(1 for w in words if w in text) / len(words)
        if score > 0.2:
            scored.append((doc_id, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in scored[:max_agents]]


@step(enable_cache=False)
def traverse_node(
    doc_id: str,
    query: str,
    budget: int,
    visited: List[str],
) -> Tuple[
    Annotated[Dict[str, Any], "traversal_result"],
    Annotated[List[str], "traverse_to"],
]:
    """Single traversal step - Pydantic AI decides: answer or go deeper?

    Args:
        doc_id: Artifact chunk from parent (creates DAG edge, contains doc ID).
        query: Search query (passed as parameter via with_options).
        budget: Remaining traversal budget.
        visited: List of already visited doc IDs.

    Returns:
        Tuple of (result_dict, traverse_to_list) as separate artifacts.
    """
    docs = _load_documents()

    if doc_id not in docs or doc_id in visited or budget <= 0:
        return {
            "doc_id": doc_id,
            "found_answer": False,
            "visited": visited,
            "budget": budget,
        }, []

    doc = docs[doc_id]
    visited = visited + [doc_id]

    # Get related documents (pre-filter to only those that exist in the graph)
    rels = doc.get("relationships", {})
    related_raw: List[str] = []
    for rel_list in rels.values():
        related_raw.extend(rel_list if isinstance(rel_list, list) else [])
    # Filter to only IDs that actually exist in the document graph
    related = [
        rid for rid in related_raw if isinstance(rid, str) and rid in docs
    ]

    # Truncate content to avoid context length errors
    content = _truncate_text(doc.get("content"), max_chars=2000)

    # Build prompt for LLM agent
    prompt = f"""
    Query: {query}

    Current document: {doc.get("title")}
    Content: {content}

    Related documents available: {related}
    Budget remaining: {budget}

    Does this document answer the query? Or should we explore related documents?
    Only choose traverse_to IDs from the provided related documents list.
    """

    global _llm_unavailable_logged
    decision: TraversalDecision

    # Check LLM availability upfront to avoid unnecessary API calls
    if not _llm_available():
        if not _llm_unavailable_logged:
            logger.warning(
                "OPENAI_API_KEY not set. Using fallback keyword matching. "
                "Set OPENAI_API_KEY for full LLM functionality."
            )
            _llm_unavailable_logged = True
        # Fallback to keyword matching
        has_answer = any(
            w in (doc.get("content") or "").lower()
            for w in query.lower().split()
        )
        decision = TraversalDecision(
            has_answer=has_answer,
            answer=_truncate_text(doc.get("content", ""), MAX_ANSWER_CHARS)
            if has_answer
            else "",
            traverse_to=related[:2] if not has_answer else [],
            reasoning="Fallback mode (OPENAI_API_KEY not set)",
        )
    else:
        try:
            agent = _get_traversal_agent()
            result = _run_agent_with_retry(agent, prompt)
            decision = result.output
        except (KeyboardInterrupt, SystemExit):
            raise
        except (ModelHTTPError, ModelAPIError, AgentRunError) as e:
            # Known LLM errors - fallback gracefully
            logger.warning(
                f"LLM agent error, using fallback: {type(e).__name__}: {e}"
            )
            has_answer = any(
                w in doc.get("content", "").lower()
                for w in query.lower().split()
            )
            decision = TraversalDecision(
                has_answer=has_answer,
                answer=_truncate_text(doc.get("content", ""), MAX_ANSWER_CHARS)
                if has_answer
                else "",
                traverse_to=related[:2] if not has_answer else [],
                reasoning=f"Fallback mode ({type(e).__name__})",
            )
        except Exception as e:
            # Unexpected errors - log with full traceback but still fallback
            logger.exception(f"Unexpected error in LLM agent: {e}")
            has_answer = any(
                w in doc.get("content", "").lower()
                for w in query.lower().split()
            )
            decision = TraversalDecision(
                has_answer=has_answer,
                answer=_truncate_text(doc.get("content", ""), MAX_ANSWER_CHARS)
                if has_answer
                else "",
                traverse_to=related[:2] if not has_answer else [],
                reasoning="Fallback mode (unexpected error)",
            )

    # Validate traverse_to IDs to prevent hallucinated document references
    validated_traverse_to = _validate_traverse_to(
        decision.traverse_to, related=related, docs=docs
    )

    result_dict = {
        "doc_id": doc_id,
        "title": doc.get("title"),
        "found_answer": decision.has_answer,
        "answer": decision.answer,
        "reasoning": decision.reasoning,
        "visited": visited,
        "budget": budget - 1,
    }

    return result_dict, validated_traverse_to


@step
def aggregate_results(
    traversal_results: List[Dict[str, Any]],
    query: str,
) -> Annotated[Dict[str, Any], "search_results"]:
    """Combine findings from all traversal agents."""
    answers = [r for r in traversal_results if r.get("found_answer")]
    all_visited = set()
    for r in traversal_results:
        all_visited.update(r.get("visited", []))

    return {
        "query": query,
        "type": "deep",
        "results": [
            {
                "doc_id": a["doc_id"],
                "title": a.get("title"),
                "answer": _truncate_text(
                    a.get("answer", ""), MAX_ANSWER_CHARS
                ),
            }
            for a in answers
        ],
        "documents_explored": len(all_visited),
        "agents_used": len(traversal_results),
    }


def _escape_html(value: Any) -> str:
    """HTML-escape a value for safe embedding into HTML text nodes."""
    if value is None:
        return ""
    return html.escape(str(value))


def _render_result_card(result: Dict[str, Any], index: int) -> str:
    """Render a single result as an HTML card.

    Args:
        result: Result dictionary with doc_id, title, answer, and optionally score.
        index: 1-based index for display.

    Returns:
        HTML string for the result card.
    """
    title = _escape_html(
        result.get("title") or result.get("doc_id", "Unknown")
    )
    doc_id = _escape_html(result.get("doc_id", ""))
    answer = result.get("answer", "")
    score = result.get("score")

    # Build the card content
    card_html = f"""
        <div class="result-card">
            <div class="result-header">
                <span class="result-number">#{index}</span>
                <div class="result-title-block">
                    <h3 class="result-title">{title}</h3>
                    <span class="result-doc-id">{doc_id}</span>
                </div>
    """

    # Add score badge for simple search results
    if score is not None:
        score_percent = int(float(score) * 100)
        card_html += f'<span class="score-badge">{score_percent}% match</span>'

    card_html += "</div>"

    # Add answer section for deep search results
    if answer:
        answer_safe = _escape_html(answer)
        # Use collapsible section for long answers (> 500 chars)
        if len(answer) > 500:
            card_html += f"""
                <details class="answer-section" open>
                    <summary class="answer-toggle">View Answer ({len(answer):,} chars)</summary>
                    <div class="answer-content">{answer_safe}</div>
                </details>
            """
        else:
            card_html += f"""
                <div class="answer-section">
                    <div class="answer-content">{answer_safe}</div>
                </div>
            """

    card_html += "</div>"
    return card_html


def _get_report_css() -> str:
    """Return the CSS styles for the HTML report."""
    return """
        /* ZenML Design System - Hierarchical Search Report */
        :root {
            --zenml-purple: #7a3ef4;
            --zenml-purple-dark: #431d93;
            --zenml-purple-light: #e4d8fd;
            --zenml-purple-lighter: #f1ebfe;
            --text-primary: #0d061d;
            --text-secondary: #6b7280;
            --surface-primary: #ffffff;
            --surface-secondary: #f9fafb;
            --border-moderate: #e5e7eb;
            --success: #1cbf4a;
            --success-light: #d2f2db;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8faff 0%, #f1f5f9 100%);
            color: var(--text-primary);
            padding: 24px;
            font-size: 14px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .report-container {
            max-width: 800px;
            margin: 0 auto;
        }

        /* Header Section */
        .report-header {
            background: var(--surface-primary);
            border: 1px solid var(--border-moderate);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .report-title {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .report-title::before {
            content: "🔍";
        }

        .query-display {
            background: var(--zenml-purple-lighter);
            border: 1px solid var(--zenml-purple-light);
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 12px;
            font-size: 15px;
            color: var(--zenml-purple-dark);
            font-style: italic;
        }

        .search-type-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .search-type-badge.deep {
            background: linear-gradient(135deg, var(--zenml-purple), var(--zenml-purple-dark));
            color: white;
        }

        .search-type-badge.simple {
            background: var(--success-light);
            color: #065f46;
        }

        /* Metrics Row */
        .metrics-row {
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .metric-card {
            flex: 1;
            min-width: 120px;
            background: var(--surface-primary);
            border: 1px solid var(--border-moderate);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        }

        .metric-value {
            font-size: 28px;
            font-weight: 700;
            color: var(--zenml-purple);
            line-height: 1;
        }

        .metric-label {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Results Section */
        .results-section {
            background: var(--surface-primary);
            border: 1px solid var(--border-moderate);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .results-header {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-moderate);
        }

        .result-card {
            background: var(--surface-secondary);
            border: 1px solid var(--border-moderate);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            transition: border-color 0.2s ease;
        }

        .result-card:last-child {
            margin-bottom: 0;
        }

        .result-card:hover {
            border-color: var(--zenml-purple-light);
        }

        .result-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }

        .result-number {
            background: var(--zenml-purple);
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            flex-shrink: 0;
        }

        .result-title-block {
            flex: 1;
            min-width: 0;
        }

        .result-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0 0 2px 0;
            word-wrap: break-word;
        }

        .result-doc-id {
            font-size: 12px;
            color: var(--text-secondary);
            font-family: 'SF Mono', Monaco, monospace;
        }

        .score-badge {
            background: var(--success-light);
            color: #065f46;
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 12px;
            flex-shrink: 0;
        }

        .answer-section {
            margin-top: 12px;
            border-top: 1px solid var(--border-moderate);
            padding-top: 12px;
        }

        .answer-toggle {
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            color: var(--zenml-purple);
            padding: 4px 0;
        }

        .answer-toggle:hover {
            color: var(--zenml-purple-dark);
        }

        .answer-content {
            background: var(--surface-primary);
            border: 1px solid var(--border-moderate);
            border-radius: 6px;
            padding: 12px;
            margin-top: 8px;
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary);
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 12px;
        }

        .empty-state-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .empty-state-description {
            font-size: 14px;
            max-width: 300px;
            margin: 0 auto;
        }

        /* Footer */
        .report-footer {
            text-align: center;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--border-moderate);
            font-size: 12px;
            color: var(--text-secondary);
        }

        .report-footer a {
            color: var(--zenml-purple);
            text-decoration: none;
        }
    """


@step
def create_report(results: Dict[str, Any]) -> Annotated[HTMLString, "report"]:
    """Generate a polished HTML visualization of search results.

    Creates a self-contained HTML document with embedded CSS following the
    ZenML design system. All user/LLM-derived content is escaped to prevent
    XSS attacks.

    Args:
        results: Search results dictionary containing query, type, results list,
                 and metrics (agents_used, documents_explored).

    Returns:
        HTMLString artifact for display in the ZenML dashboard.
    """
    query_safe = _escape_html(results.get("query", ""))
    search_type = results.get("type", "deep")
    search_type_safe = _escape_html(search_type)
    agents_used = results.get("agents_used", 0)
    result_list = results.get("results", [])
    docs_explored = results.get("documents_explored", len(result_list))
    result_count = len(result_list)

    # Build results HTML
    if result_list:
        results_html = ""
        for i, r in enumerate(result_list, 1):
            results_html += _render_result_card(r, i)
    else:
        results_html = """
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <h3 class="empty-state-title">No Results Found</h3>
                <p class="empty-state-description">
                    Try broadening your search query or increasing the search depth.
                </p>
            </div>
        """

    # Determine badge class based on search type
    badge_class = "deep" if search_type == "deep" else "simple"

    # Build the full HTML document
    report_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Report | ZenML</title>
    <style>
{_get_report_css()}
    </style>
</head>
<body>
    <div class="report-container">
        <!-- Header -->
        <div class="report-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h1 class="report-title">Hierarchical Document Search</h1>
                <span class="search-type-badge {badge_class}">{search_type_safe} Search</span>
            </div>
            <div class="query-display">"{query_safe}"</div>
        </div>

        <!-- Metrics -->
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-value">{result_count}</div>
                <div class="metric-label">Results</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{docs_explored}</div>
                <div class="metric-label">Docs Explored</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{agents_used}</div>
                <div class="metric-label">Agents Used</div>
            </div>
        </div>

        <!-- Results -->
        <div class="results-section">
            <h2 class="results-header">Search Results</h2>
            {results_html}
        </div>

        <!-- Footer -->
        <div class="report-footer">
            Generated by <a href="https://zenml.io" target="_blank">ZenML</a> Hierarchical Search Pipeline
        </div>
    </div>
</body>
</html>'''

    return HTMLString(report_html)
