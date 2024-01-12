from typing import Optional

from zenml.cli import update_model
from zenml.models.v2.base.scoped import WorkspaceScopedRequest, \
    WorkspaceScopedResponseBody
from zenml.triggers.action_models import Action
from zenml.triggers.event_models import Event

# ------------------ Request Model ------------------
class TriggerRequest(WorkspaceScopedRequest):
    """Model for creating a new Trigger."""
    name: str
    description: Optional[str]
    event: Event
    action: Action

# ------------------ Update Model ------------------

@update_model
class StackUpdate(TriggerRequest):
    """Update model for stacks."""

# ------------------ Response Model ------------------

class StackResponseBody(WorkspaceScopedResponseBody):