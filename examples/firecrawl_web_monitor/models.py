"""Typed data contracts for the Firecrawl monitoring example."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ChangeStatus = Literal["same", "changed", "new", "removed", "error"]


class MeaningfulChange(BaseModel):
    """A single meaningful change identified by Firecrawl."""

    type: str
    before: Optional[str] = None
    after: Optional[str] = None
    reason: str


class FirecrawlJudgment(BaseModel):
    """Firecrawl's optional meaningful-change judgment."""

    meaningful: bool
    confidence: str
    reason: str
    meaningful_changes: List[MeaningfulChange] = Field(
        default_factory=list, alias="meaningfulChanges"
    )

    model_config = ConfigDict(populate_by_name=True)


class FirecrawlDiff(BaseModel):
    """Text and structured diffs emitted by Firecrawl."""

    text: str = ""
    structured: Dict[str, Any] = Field(default_factory=dict, alias="json")

    model_config = ConfigDict(populate_by_name=True)


class FirecrawlPageData(BaseModel):
    """One page result from a ``monitor.page`` webhook."""

    monitor_id: str = Field(alias="monitorId")
    check_id: str = Field(alias="checkId")
    url: str
    status: ChangeStatus
    previous_scrape_id: Optional[str] = Field(
        default=None, alias="previousScrapeId"
    )
    current_scrape_id: Optional[str] = Field(
        default=None, alias="currentScrapeId"
    )
    error: Optional[str] = None
    is_meaningful: Optional[bool] = Field(default=None, alias="isMeaningful")
    judgment: Optional[FirecrawlJudgment] = None
    diff: FirecrawlDiff = Field(default_factory=FirecrawlDiff)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("diff", mode="before")
    @classmethod
    def _default_null_diff(cls, value: object) -> object:
        """Firecrawl sends an explicit null diff for baseline 'new' pages.

        Args:
            value: Raw ``diff`` value from the payload.

        Returns:
            An empty diff object when the payload contains null.
        """
        return value if value is not None else {}


class FirecrawlWebhook(BaseModel):
    """Firecrawl webhook envelope used to start the pipeline."""

    success: bool
    type: str
    id: str
    webhook_id: str = Field(alias="webhookId")
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class PageChange(BaseModel):
    """Normalized page change consumed by downstream analysis."""

    event_id: str
    monitor_id: str
    check_id: str
    url: str
    status: ChangeStatus
    previous_scrape_id: Optional[str] = None
    current_scrape_id: Optional[str] = None
    unified_diff: str = ""
    structured_diff: Dict[str, Any] = Field(default_factory=dict)
    is_meaningful: Optional[bool] = None
    firecrawl_judgment: Optional[FirecrawlJudgment] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChangeAnalysis(BaseModel):
    """Structured business analysis of a monitored page change."""

    summary: str
    impact: str
    recommended_actions: List[str]
    meaningful: bool
    confidence: str
    analyzer: str


class MonitoringReport(BaseModel):
    """Final report joining source evidence with its analysis."""

    url: str
    status: ChangeStatus
    goal: str
    analysis: ChangeAnalysis
    unified_diff: str
    monitor_id: str
    check_id: str
    event_id: str
