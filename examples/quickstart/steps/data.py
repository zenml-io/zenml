# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Data loading step for intent classification."""

from typing import Annotated, List, Tuple

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

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
    # Credit Limit (8 examples)
    ("can you increase my credit limit", "credit_limit"),
    ("i need a higher credit limit", "credit_limit"),
    ("please raise my spending limit", "credit_limit"),
    ("how do i request a credit line increase", "credit_limit"),
    ("my credit limit is too low can you help", "credit_limit"),
    ("i want to apply for a credit increase", "credit_limit"),
    ("what's the process for a credit limit increase", "credit_limit"),
    ("i need more spending power on my card", "credit_limit"),
    # Account Information (8 examples)
    ("i need to update my address", "account_info"),
    ("how do i change my phone number", "account_info"),
    ("can you update my personal information", "account_info"),
    ("i moved and need to update my details", "account_info"),
    ("how do i change my email address", "account_info"),
    ("i need to update my contact information", "account_info"),
    ("can you help me change my account settings", "account_info"),
    ("i want to update my profile", "account_info"),
    # Transfers (8 examples)
    ("i need to transfer money", "transfers"),
    ("how do i send money to another account", "transfers"),
    ("can you help me with a wire transfer", "transfers"),
    ("i want to transfer funds between accounts", "transfers"),
    ("how do i send money to my friend", "transfers"),
    ("what are your transfer limits", "transfers"),
    ("i need to move money from savings to checking", "transfers"),
    ("can you process an international transfer", "transfers"),
    # General (10 examples)
    ("hello", "general"),
    ("hi there", "general"),
    ("can you help me", "general"),
    ("thank you", "general"),
    ("good morning", "general"),
    ("i have a question about my account", "general"),
    ("what services do you offer", "general"),
    ("i need assistance with banking", "general"),
    ("how are you today", "general"),
    ("goodbye and thank you for your help", "general"),
    # More Card Lost (6 examples)
    ("please freeze my card i cant find it", "card_lost"),
    ("how do i report my card stolen", "card_lost"),
    ("need a new card mine went missing", "card_lost"),
    ("lost debit card cancel it now", "card_lost"),
    ("misplaced my credit card can you disable it", "card_lost"),
    ("i lost my atm card what now", "card_lost"),
    # More Payments (6 examples)
    ("set up autopay for my account", "payments"),
    ("why was my payment declined", "payments"),
    ("make a one time payment today", "payments"),
    ("can i change my payment date", "payments"),
    ("payment is pending how long will it take", "payments"),
    ("set a recurring monthly payment", "payments"),
    # More Account Balance (6 examples)
    ("whats my available credit right now", "account_balance"),
    ("show balance for my checking account", "account_balance"),
    ("how much can i spend before reaching my limit", "account_balance"),
    ("tell me my statement balance", "account_balance"),
    ("balance inquiry please", "account_balance"),
    ("how much do i have available to spend", "account_balance"),
    # More Dispute (6 examples)
    ("i want to file a chargeback", "dispute"),
    ("merchant charged me twice", "dispute"),
    ("charged the wrong amount", "dispute"),
    ("i didnt receive the service i paid for", "dispute"),
    ("how do i dispute a fraudulent transaction", "dispute"),
    ("there is an unauthorized withdrawal on my card", "dispute"),
    # More Credit Limit (6 examples)
    ("lower my credit limit please", "credit_limit"),
    ("temporary limit increase for travel", "credit_limit"),
    ("why was my credit limit reduced", "credit_limit"),
    ("can you review my credit line", "credit_limit"),
    ("whats my current credit limit", "credit_limit"),
    ("reduce my credit line for safety", "credit_limit"),
    # More General (6 examples)
    ("good afternoon", "general"),
    ("thanks for your help", "general"),
    ("i need support with my account", "general"),
    ("can i talk to an agent", "general"),
    ("help please", "general"),
    ("can you assist me with something", "general"),
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
