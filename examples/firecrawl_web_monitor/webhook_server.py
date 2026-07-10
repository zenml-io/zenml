"""Local FastAPI receiver that starts a ZenML run per Firecrawl page event."""

import os
import secrets
from typing import Annotated, Any, Dict

from constants import DEFAULT_GOAL
from fastapi import FastAPI, Header, HTTPException, status
from models import FirecrawlWebhook
from pipelines.monitoring import firecrawl_web_monitor_pipeline
from pydantic import BaseModel


class WebhookResponse(BaseModel):
    """Response returned after handling a Firecrawl webhook."""

    status: str
    event_id: str


def create_app() -> FastAPI:
    """Create the webhook receiver without module-level mutable state.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="Firecrawl to ZenML webhook")

    @app.post("/webhooks/firecrawl")
    def receive_firecrawl_webhook(
        event: FirecrawlWebhook,
        authorization: Annotated[str | None, Header()] = None,
    ) -> WebhookResponse:
        expected_token = os.getenv("FIRECRAWL_WEBHOOK_TOKEN")
        if expected_token and not secrets.compare_digest(
            authorization or "", f"Bearer {expected_token}"
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token.",
            )
        if event.type != "monitor.page":
            return WebhookResponse(status="ignored", event_id=event.id)

        payload: Dict[str, Any] = event.model_dump(
            by_alias=True, exclude_none=True
        )
        firecrawl_web_monitor_pipeline(
            payload=payload,
            goal=os.getenv("MONITORING_GOAL", DEFAULT_GOAL),
            notify_slack=os.getenv("NOTIFY_SLACK", "false").lower() == "true",
            llm_secret_name=os.getenv("LLM_SECRET_NAME"),
        )
        return WebhookResponse(status="completed", event_id=event.id)

    return app


app = create_app()
