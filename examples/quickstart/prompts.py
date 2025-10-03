"""Single source of truth for LLM prompts used by the quickstart example.

This module centralizes:
- Prompt templates for intent classification and response generation
- Intent-specific contexts used to condition the LLM
- Fallback template responses for non-LLM flows or errors

It is intentionally dependency-free (no OpenAI or ZenML imports) so it can be
safely imported from different execution contexts (local script runs from the
quickstart directory or orchestrated runs from the repository root).
"""

from typing import Dict

# Prompt used to classify user intent
INTENT_CLASSIFICATION_PROMPT = """You are a banking support intent classifier. Classify this customer message into one of these intents:
- card_lost: Customer lost their card or needs replacement
- payments: Questions about payments, bills, due dates
- account_balance: Balance inquiries
- dispute: Transaction disputes or fraud claims
- credit_limit: Credit limit increase requests
- general: Greetings, general help, unclear requests

Customer message: "{text}"

Respond with just the intent name (e.g., "card_lost") and a confidence score 0-1. Format: intent_name,confidence"""

# Intent contexts for response generation
INTENT_CONTEXTS: Dict[str, str] = {
    "card_lost": "The customer has lost their card and needs help with replacement. Provide clear, step-by-step instructions including freezing the card, reporting it, and getting a replacement.",
    "payments": "The customer needs help with payments. Provide information about payment methods, due dates, and how to set up automatic payments.",
    "account_balance": "The customer wants to check their account balance. Explain the different ways they can check their balance.",
    "dispute": "The customer wants to dispute a transaction. Explain the dispute process and timeline.",
    "credit_limit": "The customer wants to increase their credit limit. Explain how to request an increase.",
    "general": "Provide general banking assistance and ask what specific help they need.",
}

# Template responses for fallback
TEMPLATE_RESPONSES: Dict[str, str] = {
    "card_lost": "I understand you've lost your card. Here are the immediate steps: 1) Log into your account to freeze the card, 2) Call our 24/7 hotline at 1-800-SUPPORT, 3) Order a replacement card through the app. Your new card will arrive in 3-5 business days.",
    "payments": "For payment assistance: You can make payments through our mobile app, website, or by calling 1-800-PAY-BILL. Automatic payments can be set up in your account settings. Your next payment due date is visible in the app dashboard.",
    "account_balance": "To check your current balance: 1) Log into the mobile app or website, 2) Call our automated balance line at 1-800-BALANCE, 3) Text 'BAL' to 12345. Your balance will be displayed immediately.",
    "dispute": "To dispute a charge: 1) Log into your account and find the transaction, 2) Click 'Dispute this charge', 3) Provide details about why you're disputing it. We'll investigate within 2-3 business days and provide temporary credit if applicable.",
    "credit_limit": "For credit limit increases: You can request an increase through your online account under 'Account Services' or call 1-800-CREDIT. We'll review your account and provide a decision within 24 hours.",
    "general": "I'm here to help with your banking needs. I can assist with card issues, payments, account balances, disputes, and credit limit requests. What specific question can I help you with today?",
}

# Prompt template for response generation; use with .format(original_text=..., context=...)
RESPONSE_PROMPT_TEMPLATE = """You are a helpful banking support agent. The customer said: "{original_text}"

Context: {context}

Generate a helpful, professional response that:
1. Acknowledges their specific request
2. Provides clear, actionable steps
3. Is warm but professional
4. Includes relevant contact information or next steps
5. Keep it concise (2-3 sentences max)

Response:"""


def build_intent_classification_prompt(text: str) -> str:
    """Build the intent classification prompt for the given text."""
    return INTENT_CLASSIFICATION_PROMPT.format(text=text)


def build_response_prompt(original_text: str, intent: str) -> str:
    """Build the response generation prompt for the given text and intent.

    Falls back to the "general" context if the intent is unknown.
    """
    context = INTENT_CONTEXTS.get(intent, INTENT_CONTEXTS["general"])
    return RESPONSE_PROMPT_TEMPLATE.format(
        original_text=original_text, context=context
    )


__all__ = [
    "INTENT_CLASSIFICATION_PROMPT",
    "INTENT_CONTEXTS",
    "TEMPLATE_RESPONSES",
    "RESPONSE_PROMPT_TEMPLATE",
    "build_intent_classification_prompt",
    "build_response_prompt",
]
