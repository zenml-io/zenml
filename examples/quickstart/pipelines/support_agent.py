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

"""Agent serving pipeline that loads production classifier if available."""

from typing import Any

from steps.infer import classify_intent, generate_response
from utils import classifier_manager, load_production_classifier

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


def _load_production_classifier_if_any() -> None:
    """Find artifact version tagged 'production' and load it."""
    classifier = load_production_classifier()
    if classifier:
        classifier_manager.set_classifier(classifier)
        logger.info("[agent:init] Loaded production classifier")
    else:
        logger.info("[agent:init] No production-tagged classifier found.")


def on_init_hook(*args: Any, **kwargs: Any) -> None:
    """Initialize the agent by loading production classifier if available.

    Parameters:
        args: Unused keyword arguments from ZenML.
        kwargs: Unused keyword arguments from ZenML.
    """
    logger.debug(f"[agent:init] Args: {args}, Kwargs: {kwargs}")
    _load_production_classifier_if_any()


@pipeline(enable_cache=False, on_init=on_init_hook)
def support_agent(
    text: str = "my card is lost and i need a replacement",
    use_classifier: bool = True,
) -> Any:
    """Agent serving pipeline that optionally uses classifier.

    Args:
        text: Customer input text to process.
        use_classifier: Whether to use the trained classifier (True) or force LLM-only mode (False).

    Returns:
        JSON-formatted agent response containing intent classification and generated response.
    """
    # Classify the intent (classifier usage controlled by parameter)
    classification_result = classify_intent(text, use_classifier)

    # Generate response based on classification
    response = generate_response(classification_result)

    return response
