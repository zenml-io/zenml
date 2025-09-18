"""Inference step for agent serving pipeline."""

import json
from typing import Annotated, Any, Dict, Optional

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

# Global variable to hold the loaded classifier
_router: Optional[Any] = None


@step
def classify_intent(
    text: str,
) -> Annotated[Dict[str, Any], "classification_result"]:
    """Classify intent using loaded classifier or fall back to LLM."""
    global _router

    result = {
        "text": text,
        "intent": None,
        "confidence": 0.0,
        "intent_source": "none",
    }

    if _router is not None:
        try:
            # Use the classifier
            predicted_intent = _router.predict([text])[0]
            predicted_probabilities = _router.predict_proba([text])[0]
            max_confidence = max(predicted_probabilities)

            result.update(
                {
                    "intent": predicted_intent,
                    "confidence": float(max_confidence),
                    "intent_source": "classifier",
                }
            )
            logger.info(
                f"Classifier: '{text}' → {predicted_intent} (confidence: {max_confidence:.3f})"
            )
        except Exception as e:
            logger.error(f"Classifier error: {e}")
            result.update(
                {"intent": "general", "intent_source": "classifier_error"}
            )
    else:
        logger.info("No classifier loaded, using LLM-only mode")
        result.update({"intent": "general", "intent_source": "llm"})

    return result


@step
def generate_response(
    classification_result: Dict[str, Any],
) -> Annotated[str, "agent_response"]:
    """Generate response based on classified intent."""
    intent = classification_result.get("intent", "general")
    confidence = classification_result.get("confidence", 0.0)
    source = classification_result.get("intent_source", "none")

    # Intent-specific responses
    responses = {
        "card_lost": "I understand you've lost your card. Here are the immediate steps: 1) Log into your account to freeze the card, 2) Call our 24/7 hotline at 1-800-SUPPORT, 3) Order a replacement card through the app. Your new card will arrive in 3-5 business days.",
        "payments": "For payment assistance: You can make payments through our mobile app, website, or by calling 1-800-PAY-BILL. Automatic payments can be set up in your account settings. Your next payment due date is visible in the app dashboard.",
        "account_balance": "To check your current balance: 1) Log into the mobile app or website, 2) Call our automated balance line at 1-800-BALANCE, 3) Text 'BAL' to 12345. Your balance will be displayed immediately.",
        "dispute": "To dispute a charge: 1) Log into your account and find the transaction, 2) Click 'Dispute this charge', 3) Provide details about why you're disputing it. We'll investigate within 2-3 business days and provide temporary credit if applicable.",
        "credit_limit": "For credit limit increases: You can request an increase through your online account under 'Account Services' or call 1-800-CREDIT. We'll review your account and provide a decision within 24 hours.",
        "general": "I'm here to help with your banking needs. I can assist with card issues, payments, account balances, disputes, and credit limit requests. What specific question can I help you with today?",
    }

    response = responses.get(intent, responses["general"])

    # Add metadata to response
    metadata = {
        "intent": intent,
        "confidence": confidence,
        "intent_source": source,
    }

    logger.info(f"Generated response for intent '{intent}' (source: {source})")
    return json.dumps({"answer": response, **metadata}, indent=2)
