from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AlerterMessage(BaseModel):
    """A minimal data model to represent the content of an alert.

    This model can be extended or parsed differently by each Alerter flavor
    to produce Slack blocks, email HTML, Discord embeds, etc.
    """

    title: Optional[str] = None
    body: Optional[str] = None
    metadata: Dict[str, Any] = {}
    images: List[str] = []