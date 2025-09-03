"""LLM Utility Functions.

This module provides utilities for LLM integration using LiteLLM
with smart fallbacks when API keys are not available, and optional
Langfuse observability integration.
"""

import os
from typing import Any, Optional

from zenml.logger import get_logger

# LLM Integration
try:
    import litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

logger = get_logger(__name__)


def should_use_real_llm() -> bool:
    """Check if we should use real LLM APIs based on environment variables.

    Returns:
        True if LiteLLM is available and API keys are detected, False otherwise.
    """
    return HAS_LITELLM and bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("COHERE_API_KEY")
    )


def should_use_langfuse() -> bool:
    """Check if Langfuse observability should be enabled.

    Returns:
        True if Langfuse is available and API keys are detected, False otherwise.
    """
    return bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def configure_langfuse_callbacks() -> None:
    """Configure LiteLLM to use Langfuse callbacks if available.

    Note: LiteLLM requires Langfuse v2, not v3. If you get an error about
    'sdk_integration', please install: pip install "langfuse>=2,<3"
    """
    if not should_use_langfuse() or not HAS_LITELLM:
        return

    try:
        # Set Langfuse as callback according to documentation
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
    except Exception as e:
        if "sdk_integration" in str(e):
            logger.warning(
                "Langfuse version incompatibility detected. "
                "LiteLLM requires Langfuse v2, not v3. "
                "Please install: pip install 'langfuse>=2,<3'"
            )
        else:
            logger.warning(f"Failed to configure Langfuse callbacks: {e}")


def call_llm(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Call LLM using LiteLLM with optional Langfuse observability and fallback to mock response.

    Args:
        prompt: The prompt to send to the LLM
        model: The model to use (defaults to gpt-3.5-turbo)
        metadata: Optional metadata for Langfuse tracing

    Returns:
        LLM response text
    """
    if not should_use_real_llm():
        # Fallback to mock response
        return f"Mock response for: {prompt[:50]}..."

    try:
        # Configure Langfuse callbacks if available
        configure_langfuse_callbacks()

        # Prepare LiteLLM call parameters
        call_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.7,
        }

        # Add metadata for Langfuse if available
        if metadata and should_use_langfuse():
            call_params["metadata"] = metadata

        response = litellm.completion(**call_params)

        return (
            response.choices[0].message.content
            or f"Empty response for: {prompt[:50]}..."
        )
    except Exception as e:
        logger.warning(f"LLM call failed: {e}. Falling back to mock response.")
        return f"Fallback response for: {prompt[:50]}..."
