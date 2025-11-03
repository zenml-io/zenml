"""Simple step for the quickstart pipeline."""

from typing import Optional

from zenml import step


@step
def simple_step(name: Optional[str] = None) -> str:
    """A simple step that returns a personalized greeting.

    This is the simplest possible ZenML step. It:
    1. Takes an optional input parameter
    2. Returns a string
    3. Is automatically tracked as an artifact by ZenML

    Args:
        name: Optional name to personalize the greeting

    Returns:
        A personalized greeting message
    """
    if name:
        message = f"Hello {name}! Welcome to ZenML 🚀"
    else:
        message = "Hello from ZenML! 🚀"
    print(message)
    return message
