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

"""Utility functions for the quickstart example."""

import os
from typing import Any, Dict, Optional, Type

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

# Import prompt templates and builders in a way that works both when running
# from the quickstart directory (local script) and from the repo root (orchestrated).
try:
    from prompts import (
        TEMPLATE_RESPONSES,
        build_intent_classification_prompt,
        build_response_prompt,
    )
except (
    Exception
):  # Fallback when importing via implicit namespace packages from repo root
    from examples.quickstart.prompts import (
        TEMPLATE_RESPONSES,
        build_intent_classification_prompt,
        build_response_prompt,
    )

# Constants
DEFAULT_MODEL = "gpt-3.5-turbo"
INTENT_TEMPERATURE = 0.1
RESPONSE_TEMPERATURE = 0.7

# LLM Integration
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ClassifierManager:
    """Singleton to manage classifier state across pipeline steps."""

    _instance: Optional["ClassifierManager"] = None
    _classifier: Optional[Any] = None

    def __new__(cls: Type["ClassifierManager"]) -> "ClassifierManager":
        """Create singleton instance.

        Returns:
            The singleton ClassifierManager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_classifier(self, classifier: Any) -> None:
        """Store the loaded classifier.

        Args:
            classifier: The trained classifier to store.
        """
        self._classifier = classifier

    def get_classifier(self) -> Optional[Any]:
        """Retrieve the stored classifier.

        Returns:
            The stored classifier or None if not set.
        """
        return self._classifier

    def has_classifier(self) -> bool:
        """Check if a classifier is loaded.

        Returns:
            True if classifier is loaded, False otherwise.
        """
        return self._classifier is not None


# Global instance
classifier_manager = ClassifierManager()


def call_llm_for_intent(text: str) -> Dict[str, Any]:
    """Use LLM to classify intent and provide confidence.

    Args:
        text: Customer input text to classify.

    Returns:
        Dictionary with intent, confidence, and source information.
    """
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

        prompt = build_intent_classification_prompt(text)

        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=INTENT_TEMPERATURE,
            max_tokens=50,
        )

        result = response.choices[0].message.content
        logger.debug(f"LLM raw response: {result}")
        if result is None:
            result = "general,0.5"
        else:
            result = result.strip()

        # Parse response (e.g., "card_lost,0.85")
        try:
            if "," in result:
                intent, conf_str = result.split(",", 1)
                confidence = float(conf_str.strip())
            else:
                intent = result.strip()
                confidence = 0.8
        except (ValueError, AttributeError):
            intent = "general"
            confidence = 0.5

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
    """Simulate generic banking response without intent classification.

    For evaluation purposes, this always returns 'general' intent to simulate
    the LLM-only mode where no intent classification occurs.

    Args:
        text: Customer input text (used for logging only).

    Returns:
        Dictionary with 'general' intent for LLM-only mode simulation.
    """
    logger.info(f"LLM Generic: '{text}' → general (generic response)")

    return {
        "intent": "general",
        "confidence": 0.5,
        "intent_source": "llm_generic",
    }


def generate_llm_response(original_text: str, intent: str) -> str:
    """Generate personalized response using LLM.

    Args:
        original_text: The customer's original input text.
        intent: The classified intent for the response.

    Returns:
        Generated response string tailored to the intent.
    """
    if not OPENAI_AVAILABLE:
        return get_template_response(intent)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return get_template_response(intent)

    try:
        client = OpenAI(api_key=api_key)

        prompt = build_response_prompt(original_text, intent)

        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=RESPONSE_TEMPERATURE,
            max_tokens=150,
        )

        content = response.choices[0].message.content
        return content.strip() if content else get_template_response(intent)

    except Exception as e:
        logger.error(f"LLM response generation failed: {e}")
        return get_template_response(intent)


def get_template_response(intent: str) -> str:
    """Fallback template responses.

    Args:
        intent: The intent for which to get a template response.

    Returns:
        Template response string for the given intent.
    """
    return TEMPLATE_RESPONSES.get(intent, TEMPLATE_RESPONSES["general"])


def load_production_classifier() -> Optional[Any]:
    """Load the production-tagged classifier from the artifact store.

    Returns:
        The loaded classifier model or None if not found.
    """
    try:
        client = Client()
        versions = client.list_artifact_versions(
            name="intent-classifier", tag="production"
        )

        # Find the most recent version tagged with 'production'
        prod_version = None
        for version in sorted(versions, key=lambda v: v.created, reverse=True):
            if version.tags:
                tag_names = [tag.name for tag in version.tags]
                if "production" in tag_names:
                    prod_version = version
                    break

        if prod_version:
            classifier = prod_version.load()
            logger.info(
                f"Loaded production classifier (version: {prod_version.version})"
            )
            return classifier
        else:
            logger.info("No production-tagged classifier found.")
            return None

    except Exception as e:
        logger.error(f"Error loading classifier: {e}")
        return None
