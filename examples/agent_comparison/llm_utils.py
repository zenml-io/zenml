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

# Langfuse Integration
try:
    from langfuse.callback import CallbackHandler

    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False

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
    return HAS_LANGFUSE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def get_langfuse_callback() -> Optional[Any]:
    """Get Langfuse callback handler if available.

    Returns:
        Langfuse callback handler or None if not available.
    """
    if not should_use_langfuse():
        return None

    try:
        return CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse callback: {e}")
        return None


def call_llm(
    prompt: str, model: str = "gpt-3.5-turbo", metadata: Optional[dict] = None
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
        # Prepare LiteLLM call parameters
        call_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.7,
        }

        # Add Langfuse callback if available
        langfuse_callback = get_langfuse_callback()
        if langfuse_callback:
            call_params["callbacks"] = [langfuse_callback]
            if metadata:
                call_params["metadata"] = metadata

        response = litellm.completion(**call_params)

        return (
            response.choices[0].message.content
            or f"Empty response for: {prompt[:50]}..."
        )
    except Exception as e:
        logger.warning(f"LLM call failed: {e}. Falling back to mock response.")
        return f"Fallback response for: {prompt[:50]}..."
