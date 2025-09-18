"""Data loading step for intent classification."""

from typing import Annotated, List, Tuple

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

# Small toy dataset for intent classification
INTENT_DATA = [
    ("my card is lost and i need a replacement", "card_lost"),
    ("i lost my credit card can you help", "card_lost"),
    ("my card was stolen what should i do", "card_lost"),
    ("help my card is missing", "card_lost"),
    ("i need to make a payment", "payments"),
    ("how do i pay my bill", "payments"),
    ("when is my payment due", "payments"),
    ("i want to set up automatic payments", "payments"),
    ("what is my current balance", "account_balance"),
    ("how much do i owe", "account_balance"),
    ("check my account balance please", "account_balance"),
    ("i want to dispute a charge", "dispute"),
    ("this transaction is wrong", "dispute"),
    ("i didnt make this purchase", "dispute"),
    ("can you increase my credit limit", "credit_limit"),
    ("i need a higher credit limit", "credit_limit"),
    ("hello", "general"),
    ("hi there", "general"),
    ("can you help me", "general"),
    ("thank you", "general"),
]


@step
def load_toy_intent_data() -> Tuple[
    Annotated[List[str], "texts"], Annotated[List[str], "labels"]
]:
    """Load small toy dataset for intent classification."""
    texts, labels = zip(*INTENT_DATA)
    logger.info(
        f"Loaded {len(texts)} training examples across {len(set(labels))} intents:"
    )
    for intent in sorted(set(labels)):
        count = labels.count(intent)
        logger.info(f"  - {intent}: {count} examples")

    return list(texts), list(labels)
