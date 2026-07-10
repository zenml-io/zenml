"""Analyze a normalized website change."""

from typing import Annotated, Optional

from analysis import DEFAULT_MODEL, analyze_change
from models import ChangeAnalysis, PageChange

from zenml import ArtifactConfig, log_metadata, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def _load_llm_credentials(
    secret_name: Optional[str],
) -> tuple[Optional[str], str]:
    """Load optional LLM credentials from the ZenML secret store."""
    if not secret_name:
        return None, DEFAULT_MODEL
    try:
        values = Client().get_secret(secret_name).secret_values
    except (KeyError, RuntimeError, ValueError):
        logger.warning(
            "ZenML secret '%s' was not found; using offline analysis.",
            secret_name,
        )
        return None, DEFAULT_MODEL
    return values.get("OPENAI_API_KEY"), values.get(
        "OPENAI_MODEL", DEFAULT_MODEL
    )


@step
def analyze_page_change(
    change: PageChange, goal: str, llm_secret_name: Optional[str]
) -> Annotated[
    ChangeAnalysis,
    ArtifactConfig(name="web_change_analysis", tags=["analysis", "llm"]),
]:
    """Interpret the diff in terms of a business goal.

    Args:
        change: Normalized web page change.
        goal: Business goal for monitoring.
        llm_secret_name: ZenML secret containing ``OPENAI_API_KEY``.

    Returns:
        Structured change analysis.
    """
    api_key, model = _load_llm_credentials(llm_secret_name)
    analysis = analyze_change(
        change=change, goal=goal, api_key=api_key, model=model
    )
    log_metadata(
        {
            "change_analysis": {
                "analyzer": analysis.analyzer,
                "meaningful": analysis.meaningful,
                "confidence": analysis.confidence,
                "status": change.status,
                "url": change.url,
            }
        }
    )
    return analysis
