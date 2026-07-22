"""Analysis helpers kept separate from ZenML orchestration for testability."""

import json
from typing import Any, Dict, Optional

from models import ChangeAnalysis, PageChange

DEFAULT_MODEL = "gpt-5-mini"


def analyze_change(
    change: PageChange,
    goal: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> ChangeAnalysis:
    """Analyze a change with OpenAI or a deterministic local fallback.

    Args:
        change: Normalized page change.
        goal: Business goal that defines which changes matter.
        api_key: Optional OpenAI API key loaded from a ZenML secret.
        model: OpenAI model name.

    Returns:
        A structured analysis suitable for alerting and later comparison.
    """
    if api_key:
        return _analyze_with_openai(
            change=change, goal=goal, api_key=api_key, model=model
        )
    return _analyze_without_llm(change=change)


def _analyze_with_openai(
    change: PageChange, goal: str, api_key: str, model: str
) -> ChangeAnalysis:
    """Ask OpenAI for a structured interpretation of the diff."""
    from openai import OpenAI

    prompt = (
        "Analyze this website change against the monitoring goal. "
        "Return JSON with summary, impact, recommended_actions (a list), "
        "meaningful (boolean), and confidence (low, medium, or high).\n\n"
        f"Goal: {goal}\nURL: {change.url}\nStatus: {change.status}\n"
        f"Unified diff:\n{change.unified_diff[:12000]}\n"
        f"Structured diff:\n{json.dumps(change.structured_diff)[:6000]}"
    )
    response = OpenAI(api_key=api_key).chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise web-change analyst. Base conclusions "
                    "only on the supplied evidence and return valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The LLM returned an empty analysis.")
    result: Dict[str, Any] = json.loads(content)
    result.pop("analyzer", None)
    return ChangeAnalysis(
        **result,
        analyzer=model,
    )


def _analyze_without_llm(change: PageChange) -> ChangeAnalysis:
    """Produce a useful offline result from Firecrawl's own evidence."""
    judgment = change.firecrawl_judgment
    if judgment:
        actions = [item.reason for item in judgment.meaningful_changes]
        return ChangeAnalysis(
            summary=judgment.reason,
            impact=(
                "The change matches the configured monitoring goal."
                if judgment.meaningful
                else "The change appears to be noise for the monitoring goal."
            ),
            recommended_actions=actions or ["Review the recorded diff."],
            meaningful=judgment.meaningful,
            confidence=judgment.confidence,
            analyzer="firecrawl-judgment-fallback",
        )

    changed_lines = [
        line
        for line in change.unified_diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    return ChangeAnalysis(
        summary=f"Firecrawl reported {change.status} with {len(changed_lines)} changed lines.",
        impact="An LLM was not configured, so business impact was not inferred.",
        recommended_actions=["Review the recorded diff."],
        meaningful=change.status in {"changed", "new", "removed"},
        confidence="low",
        analyzer="deterministic-fallback",
    )
