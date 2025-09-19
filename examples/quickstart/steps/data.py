"""Data loading step for intent classification."""

from typing import Annotated, List, Tuple

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

# Expanded dataset for intent classification with more diverse examples
INTENT_DATA = [
    # Card Lost (10 examples)
    ("my card is lost and i need a replacement", "card_lost"),
    ("i lost my credit card can you help", "card_lost"),
    ("my card was stolen what should i do", "card_lost"),
    ("help my card is missing", "card_lost"),
    ("i cannot find my debit card anywhere", "card_lost"),
    ("someone took my card how do i report it", "card_lost"),
    ("my wallet was stolen with my card inside", "card_lost"),
    ("i need to cancel my card immediately it's gone", "card_lost"),
    ("card replacement please mine is lost", "card_lost"),
    ("urgent my card is missing and i need help", "card_lost"),
    # Payments (10 examples)
    ("i need to make a payment", "payments"),
    ("how do i pay my bill", "payments"),
    ("when is my payment due", "payments"),
    ("i want to set up automatic payments", "payments"),
    ("can you help me schedule a payment", "payments"),
    ("my payment failed how do i try again", "payments"),
    ("what payment methods do you accept", "payments"),
    ("i need to pay my credit card bill", "payments"),
    ("how much is my minimum payment this month", "payments"),
    ("can i make a partial payment today", "payments"),
    # Account Balance (8 examples)
    ("what is my current balance", "account_balance"),
    ("how much do i owe", "account_balance"),
    ("check my account balance please", "account_balance"),
    ("can you tell me my available balance", "account_balance"),
    ("what's my remaining credit limit", "account_balance"),
    ("how much money is in my account", "account_balance"),
    ("show me my account summary", "account_balance"),
    ("what's my outstanding balance", "account_balance"),
    # Dispute (8 examples)
    ("i want to dispute a charge", "dispute"),
    ("this transaction is wrong", "dispute"),
    ("i didnt make this purchase", "dispute"),
    ("there's a fraudulent charge on my account", "dispute"),
    ("i need to report unauthorized transactions", "dispute"),
    ("this charge is incorrect please fix it", "dispute"),
    ("someone used my card without permission", "dispute"),
    ("i don't recognize this transaction", "dispute"),
    # Credit Limit (6 examples)
    ("can you increase my credit limit", "credit_limit"),
    ("i need a higher credit limit", "credit_limit"),
    ("please raise my spending limit", "credit_limit"),
    ("how do i request a credit line increase", "credit_limit"),
    ("my credit limit is too low can you help", "credit_limit"),
    ("i want to apply for a credit increase", "credit_limit"),
    # General (8 examples)
    ("hello", "general"),
    ("hi there", "general"),
    ("can you help me", "general"),
    ("thank you", "general"),
    ("good morning", "general"),
    ("i have a question about my account", "general"),
    ("what services do you offer", "general"),
    ("i need assistance with banking", "general"),
]


@step
def load_toy_intent_data() -> Tuple[
    Annotated[List[str], "texts"], Annotated[List[str], "labels"]
]:
    """Load small toy dataset for intent classification.

    Returns:
        Tuple of (texts, labels) for training the intent classifier.
    """
    texts, labels = zip(*INTENT_DATA)
    logger.info(
        f"Loaded {len(texts)} training examples across {len(set(labels))} intents:"
    )
    for intent in sorted(set(labels)):
        count = labels.count(intent)
        logger.info(f"  - {intent}: {count} examples")

    return list(texts), list(labels)
