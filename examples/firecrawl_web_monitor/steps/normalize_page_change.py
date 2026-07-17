"""Normalize a Firecrawl page event."""

from typing import Annotated

from models import FirecrawlPageData, FirecrawlWebhook, PageChange

from zenml import ArtifactConfig, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def normalize_page_change(
    event: FirecrawlWebhook,
) -> Annotated[
    PageChange,
    ArtifactConfig(name="web_page_change", tags=["firecrawl", "diff"]),
]:
    """Convert a page result into a stable internal contract.

    Args:
        event: Validated Firecrawl event.

    Returns:
        A normalized page change.
    """
    # Firecrawl delivers one monitor.page event per page, and the API-pull
    # path emits one single-page payload per page. A multi-page event would
    # therefore be a misconfiguration; warn so the dropped pages are visible.
    if len(event.data) > 1:
        logger.warning(
            "Firecrawl event %s carries %d pages; only the first is "
            "normalized.",
            event.id,
            len(event.data),
        )
    page = FirecrawlPageData.model_validate(event.data[0])
    return PageChange(
        event_id=event.id,
        monitor_id=page.monitor_id,
        check_id=page.check_id,
        url=page.url,
        status=page.status,
        previous_scrape_id=page.previous_scrape_id,
        current_scrape_id=page.current_scrape_id,
        unified_diff=page.diff.text,
        structured_diff=page.diff.structured,
        is_meaningful=page.is_meaningful,
        firecrawl_judgment=page.judgment,
        metadata=event.metadata,
    )
