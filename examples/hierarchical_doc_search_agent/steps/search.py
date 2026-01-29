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

DEFAULT_MODEL = "openai:gpt-4o-mini"
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL)

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
            If not: set has_answer=False and list document IDs to explore in traverse_to.""",
        )
    return _traversal_agent


def _llm_available() -> bool:
    """Check if LLM calls should be attempted (API key present)."""
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
        except (ModelHTTPError, ModelAPIError, AgentRunError) as e:
            last_exception = e
            if not _is_transient_error(e) or attempt == max_retries:
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
    """Return text truncated to max_chars (safe for None)."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _validate_traverse_to(
    traverse_to: List[str],
    *,
    related: List[str],
    docs: Dict[str, Any],
) -> List[str]:
    """Filter traversal targets to permitted document IDs only."""
    allowed = set(related) | set(docs.keys())
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
    """Load document graph from JSON file."""
    search_paths = [
        Path(__file__).parent.parent / "data" / "doc_graph.json",
        Path("/app/data/doc_graph.json"),  # Docker container path
        Path("data/doc_graph.json"),  # Relative fallback
    ]
    for doc_path in search_paths:
        if doc_path.exists():
            with open(doc_path) as f:
                data: Dict[str, Any] = json.load(f)
                docs: Dict[str, Any] = data["documents"]
                return docs
    logger.warning(f"Document graph not found in any of: {search_paths}")
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

    # Get related documents
    rels = doc.get("relationships", {})
    related = []
    for rel_list in rels.values():
        related.extend(rel_list if isinstance(rel_list, list) else [])

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
            w in doc.get("content", "").lower() for w in query.lower().split()
        )
        decision = TraversalDecision(
            has_answer=has_answer,
            answer=doc.get("content", "")[:200] if has_answer else "",
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
                answer=doc.get("content", "")[:200] if has_answer else "",
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
                answer=doc.get("content", "")[:200] if has_answer else "",
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
                "answer": a.get("answer", "")[:200],
            }
            for a in answers
        ],
        "documents_explored": len(all_visited),
        "agents_used": len(traversal_results),
    }


@step
def create_report(results: Dict[str, Any]) -> Annotated[HTMLString, "report"]:
    """Generate HTML visualization."""
    html = f"""
    <h2>Search: {results["query"]}</h2>
    <p><b>Type:</b> {results["type"]} | <b>Agents:</b> {results.get("agents_used", 0)} |
       <b>Docs explored:</b> {results.get("documents_explored", len(results.get("results", [])))}</p>
    <hr>
    """
    for r in results.get("results", []):
        html += "<div style='margin:10px;padding:10px;border:1px solid #ccc'>"
        html += f"<b>{r.get('title', r.get('doc_id'))}</b><br>"
        if r.get("answer"):
            html += f"<p>{r['answer']}</p>"
        html += "</div>"
    return HTMLString(html)
