"""Utility functions for the quickstart example."""

import os
from typing import Any, Dict

from zenml.logger import get_logger

logger = get_logger(__name__)

# LLM Integration
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ClassifierManager:
    """Singleton to manage classifier state across pipeline steps."""

    _instance = None
    _router = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_classifier(self, classifier):
        """Store the loaded classifier."""
        self._router = classifier

    def get_classifier(self):
        """Retrieve the stored classifier."""
        return self._router

    def has_classifier(self):
        """Check if a classifier is loaded."""
        return self._router is not None


# Global instance
classifier_manager = ClassifierManager()


def call_llm_for_intent(text: str) -> Dict[str, Any]:
    """Use LLM to classify intent and provide confidence."""
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI not available, using fallback")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "fallback",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, using fallback")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "fallback",
        }

    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""You are a banking support intent classifier. Classify this customer message into one of these intents:
- card_lost: Customer lost their card or needs replacement
- payments: Questions about payments, bills, due dates
- account_balance: Balance inquiries
- dispute: Transaction disputes or fraud claims
- credit_limit: Credit limit increase requests
- general: Greetings, general help, unclear requests

Customer message: "{text}"

Respond with just the intent name (e.g., "card_lost") and a confidence score 0-1. Format: intent_name,confidence"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50,
        )

        result = response.choices[0].message.content.strip()

        # Parse response (e.g., "card_lost,0.85")
        if "," in result:
            intent, conf_str = result.split(",", 1)
            confidence = float(conf_str.strip())
        else:
            intent = result.strip()
            confidence = 0.8

        logger.info(f"LLM: '{text}' → {intent} (confidence: {confidence:.3f})")

        return {
            "intent": intent,
            "confidence": confidence,
            "intent_source": "llm",
        }

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "llm_error",
        }


def call_llm_generic_response(text: str) -> Dict[str, Any]:
    """Use LLM to provide generic banking response without intent classification."""
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI not available, using fallback")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "fallback",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, using fallback")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "fallback",
        }

    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""You are a generic banking support assistant. A customer says: "{text}"

Provide a generic, helpful banking response without trying to classify their specific intent. Keep it general and redirect them to contact support for specific help."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )

        result = response.choices[0].message.content.strip()

        # Log the result - everything goes to "general" for LLM-only mode
        logger.info(f"LLM Generic: '{text}' → general (generic response)")

        return {
            "intent": "general",
            "confidence": 0.5,
            "intent_source": "llm_generic",
        }

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "intent": "general",
            "confidence": 0.0,
            "intent_source": "llm_error",
        }


def generate_llm_response(original_text: str, intent: str) -> str:
    """Generate personalized response using LLM."""
    if not OPENAI_AVAILABLE:
        return get_template_response(intent)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return get_template_response(intent)

    try:
        client = OpenAI(api_key=api_key)

        # Create context-aware prompt based on intent
        intent_contexts = {
            "card_lost": "The customer has lost their card and needs help with replacement. Provide clear, step-by-step instructions including freezing the card, reporting it, and getting a replacement.",
            "payments": "The customer needs help with payments. Provide information about payment methods, due dates, and how to set up automatic payments.",
            "account_balance": "The customer wants to check their account balance. Explain the different ways they can check their balance.",
            "dispute": "The customer wants to dispute a transaction. Explain the dispute process and timeline.",
            "credit_limit": "The customer wants to increase their credit limit. Explain how to request an increase.",
            "general": "Provide general banking assistance and ask what specific help they need.",
        }

        context = intent_contexts.get(intent, intent_contexts["general"])

        prompt = f"""You are a helpful banking support agent. The customer said: "{original_text}"

Context: {context}

Generate a helpful, professional response that:
1. Acknowledges their specific request
2. Provides clear, actionable steps
3. Is warm but professional
4. Includes relevant contact information or next steps
5. Keep it concise (2-3 sentences max)

Response:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"LLM response generation failed: {e}")
        return get_template_response(intent)


def get_template_response(intent: str) -> str:
    """Fallback template responses."""
    responses = {
        "card_lost": "I understand you've lost your card. Here are the immediate steps: 1) Log into your account to freeze the card, 2) Call our 24/7 hotline at 1-800-SUPPORT, 3) Order a replacement card through the app. Your new card will arrive in 3-5 business days.",
        "payments": "For payment assistance: You can make payments through our mobile app, website, or by calling 1-800-PAY-BILL. Automatic payments can be set up in your account settings. Your next payment due date is visible in the app dashboard.",
        "account_balance": "To check your current balance: 1) Log into the mobile app or website, 2) Call our automated balance line at 1-800-BALANCE, 3) Text 'BAL' to 12345. Your balance will be displayed immediately.",
        "dispute": "To dispute a charge: 1) Log into your account and find the transaction, 2) Click 'Dispute this charge', 3) Provide details about why you're disputing it. We'll investigate within 2-3 business days and provide temporary credit if applicable.",
        "credit_limit": "For credit limit increases: You can request an increase through your online account under 'Account Services' or call 1-800-CREDIT. We'll review your account and provide a decision within 24 hours.",
        "general": "I'm here to help with your banking needs. I can assist with card issues, payments, account balances, disputes, and credit limit requests. What specific question can I help you with today?",
    }
    return responses.get(intent, responses["general"])
