from typing import Optional

from zenml import step
from zenml.client import Client
from zenml.models.v2.misc.alerter_models import AlerterMessage

@step
def alerter_post_step(msg: AlerterMessage) -> bool:
    """Generic pipeline step that posts a message to the active alerter.

    This step is part of our new unified approach to sending alerts.

    Args:
        msg: The message payload to post via the alerter.

    Returns:
        True if the alerter successfully posted the message, else False.
    """
    alerter = Client().active_stack.alerter
    if not alerter:
        raise RuntimeError("No alerter is configured in the active stack.")

    # Now that we've updated Phase 2, pass the entire AlerterMessage object:
    return alerter.post(message=msg)