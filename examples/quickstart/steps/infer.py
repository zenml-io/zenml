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

"""Inference step for agent serving pipeline."""

import json
from typing import Annotated, Any, Dict

from utils import (
    call_llm_generic_response,
    classifier_manager,
    generate_llm_response,
)

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def classify_intent(
    text: str,
    use_classifier: bool = True,
) -> Annotated[Dict[str, Any], "classification_result"]:
    """Classify intent using loaded classifier or fall back to LLM.

    Args:
        text: Customer input text.
        use_classifier: Whether to use the trained classifier (True) or force LLM-only mode (False).

    Returns:
        Dictionary containing intent, confidence, source, and input text.
    """
    result = {
        "text": text,
        "intent": None,
        "confidence": 0.0,
        "intent_source": "none",
    }

    classifier = classifier_manager.get_classifier()
    if classifier is not None and use_classifier:
        try:
            # Use the trained classifier
            predicted_intent = classifier.predict([text])[0]
            predicted_probabilities = classifier.predict_proba([text])[0]
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
        # Classifier disabled or not available - use LLM for intent classification
        if not use_classifier and classifier is not None:
            logger.info(
                "Classifier disabled by parameter, using LLM for intent classification"
            )
        elif classifier is None:
            logger.info(
                "No classifier loaded, using LLM for intent classification"
            )
        else:
            logger.info("Using LLM for intent classification")
        llm_result = call_llm_generic_response(text)
        result.update(llm_result)

    # Log step metadata about classification
    log_metadata(
        metadata={
            "classification_results": {
                "intent": result["intent"],
                "confidence": result["confidence"],
                "method": result["intent_source"],
                "input_length": len(text),
            },
            "system_state": {
                "classifier_loaded": classifier_manager.has_classifier(),
                "classifier_enabled": use_classifier,
                "mode": "hybrid"
                if classifier_manager.has_classifier() and use_classifier
                else "llm_only",
            },
        }
    )

    return result


@step
def generate_response(
    classification_result: Dict[str, Any],
) -> Annotated[str, "agent_response"]:
    """Generate response based on classified intent.

    Args:
        classification_result: Dictionary containing intent classification results.

    Returns:
        JSON-formatted string containing the agent response and metadata.
    """
    intent = classification_result.get("intent", "general")
    confidence = classification_result.get("confidence", 0.0)
    source = classification_result.get("intent_source", "none")
    original_text = classification_result.get("text", "")

    # Generate response based on whether we have classifier or using pure LLM
    if source == "classifier":
        # Phase 3: Hybrid mode - Fast intent detection + Personalized LLM response
        response = generate_llm_response(original_text, intent)
        response_mode = "hybrid"
    else:
        # Phase 1: Pure LLM mode - LLM does both intent detection and response
        response = generate_llm_response(original_text, intent)
        response_mode = "llm_only"

    metadata = {
        "intent": intent,
        "confidence": confidence,
        "intent_source": source,
        "response_mode": response_mode,
    }

    log_metadata(
        metadata={
            "response_details": {
                "mode": response_mode,
                "intent_processed": intent,
                "confidence_used": confidence,
                "response_length": len(response),
            },
            "agent_evolution": {
                "phase": "hybrid" if source == "classifier" else "llm_only",
                "intelligence_type": response_mode,
            },
        }
    )

    logger.info(
        f"Generated {response_mode} response for intent '{intent}' (source: {source})"
    )
    return json.dumps({"answer": response, **metadata}, indent=2)
