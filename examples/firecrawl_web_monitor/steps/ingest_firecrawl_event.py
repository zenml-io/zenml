"""Ingest and validate a Firecrawl webhook event."""

from typing import Annotated, Any, Dict

from models import FirecrawlWebhook

from zenml import ArtifactConfig, log_metadata, step


@step
def ingest_firecrawl_event(
    payload: Dict[str, Any],
) -> Annotated[
    FirecrawlWebhook,
    ArtifactConfig(name="firecrawl_monitor_event", tags=["firecrawl", "raw"]),
]:
    """Validate and version the raw webhook envelope.

    Args:
        payload: Firecrawl webhook JSON.

    Returns:
        The validated webhook event.
    """
    event = FirecrawlWebhook.model_validate(payload)
    if event.type != "monitor.page":
        raise ValueError(
            f"Expected a 'monitor.page' event, received '{event.type}'."
        )
    if not event.data:
        raise ValueError("The Firecrawl event does not contain a page result.")
    log_metadata(
        {
            "firecrawl_event": {
                "event_id": event.id,
                "event_type": event.type,
                "page_count": len(event.data),
            }
        }
    )
    return event
