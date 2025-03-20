from typing import Optional
from zenml import step
from zenml.client import Client
from zenml.models.v2.misc.alerter_models import AlerterMessage


@step
def alerter_ask_step(msg: AlerterMessage) -> bool:
    """Generic pipeline step that asks for user approval from the active alerter.

    If the underlying alerter implements interactive logic (Slack, Discord),
    this returns True if approved, else False. If the alerter doesn't
    implement interactive logic (like SMTPEmailAlerter), a NotImplementedError
    or similar may be raised.

    Args:
        msg: The message payload to send (potentially including title, body).

    Returns:
        True if the user approved the operation, else False.

    Raises:
        RuntimeError: If no alerter is configured in the active stack.
    """
    alerter = Client().active_stack.alerter
    if not alerter:
        raise RuntimeError("No alerter is configured in the active stack.")

    return alerter.ask(question=msg)