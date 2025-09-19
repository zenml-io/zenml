"""Agent serving pipeline that loads production classifier if available."""

from typing import Any

from steps.infer import classify_intent, generate_response

# Import classifier manager
from utils import classifier_manager

from zenml import pipeline
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def _load_production_classifier_if_any() -> None:
    """Find artifact version tagged 'production' and load it."""
    try:
        client = Client()
        versions = client.list_artifact_versions(name="intent-classifier")

        # Find the version tagged with 'production'
        prod_version = None
        for version in versions:
            if version.tags:
                tag_names = [tag.name for tag in version.tags]
                if "production" in tag_names:
                    prod_version = version
                    break

        if prod_version:
            classifier = prod_version.load()
            classifier_manager.set_classifier(classifier)
            logger.info(
                f"[agent:init] Loaded production classifier (version: {prod_version.version})"
            )
        else:
            logger.info("[agent:init] No production-tagged classifier found.")

    except Exception as e:
        logger.error(f"[agent:init] Error loading classifier: {e}")


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
