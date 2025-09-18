"""Agent serving pipeline that loads production classifier if available."""

from typing import Any, Optional

from steps.infer import classify_intent, generate_response

from zenml import pipeline
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

# Global variable to store the loaded classifier
_router: Optional[Any] = None


def _load_production_classifier_if_any() -> None:
    """Find artifact version tagged 'production' and load it."""
    global _router

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
            _router = prod_version.load()
            logger.info(
                f"[agent:init] Loaded production classifier (version: {prod_version.version})"
            )

            # Update the global variable in the infer module
            import steps.infer

            steps.infer._router = _router
        else:
            logger.info("[agent:init] No production-tagged classifier found.")

    except Exception as e:
        logger.error(f"[agent:init] Error loading classifier: {e}")


def on_init_hook(**_: Any) -> None:
    """Initialize the agent by loading production classifier if available."""
    _load_production_classifier_if_any()


@pipeline(enable_cache=False, on_init=on_init_hook)
def agent_serving_pipeline(
    text: str = "my card is lost and i need a replacement",
    confidence_threshold: float = 0.65,
) -> Any:
    """Agent serving pipeline that uses classifier if available."""
    # Classify the intent
    classification_result = classify_intent(text, confidence_threshold)

    # Generate response based on classification
    response = generate_response(classification_result)

    return response
