"""Search steps for hierarchical document traversal."""

import json
from pathlib import Path
from typing import Annotated, Any, Dict, List, Tuple

from pydantic import BaseModel
from pydantic_ai import Agent

from zenml import step
from zenml.types import HTMLString

# --- Data loading ---


def _load_documents() -> Dict[str, Any]:
    """Load document graph from JSON file."""
    paths = [
        Path(__file__).parent.parent / "data" / "doc_graph.json",
        Path("data/doc_graph.json"),
    ]
    for p in paths:
        if p.exists():
            return json.load(open(p))["documents"]
    return {}


# --- Pydantic AI Agent for traversal decisions ---


class TraversalDecision(BaseModel):
    """Agent's decision: answer the query or traverse deeper."""

    has_answer: bool
    answer: str = ""
    traverse_to: List[str] = []  # doc IDs to explore next
    reasoning: str = ""


traversal_agent = Agent(
    "openai:gpt-4o-mini",
    output_type=TraversalDecision,
    system_prompt="""You are a document search agent. Given a query and document content,
    decide whether this document answers the query or if you should explore related documents.

    If the document answers the query: set has_answer=True and provide the answer.
    If not: set has_answer=False and list document IDs to explore in traverse_to.""",
)


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

    # Pydantic AI agent makes the decision
    prompt = f"""
    Query: {query}

    Current document: {doc.get("title")}
    Content: {doc.get("content")}

    Related documents available: {related}
    Budget remaining: {budget}

    Does this document answer the query? Or should we explore related documents?
    """

    try:
        result = traversal_agent.run_sync(prompt)
        decision = result.output
    except Exception:
        # Fallback if no API key
        has_answer = any(
            w in doc.get("content", "").lower() for w in query.lower().split()
        )
        decision = TraversalDecision(
            has_answer=has_answer,
            answer=doc.get("content", "")[:200] if has_answer else "",
            traverse_to=related[:2] if not has_answer else [],
            reasoning="Fallback mode",
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

    return result_dict, decision.traverse_to


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
