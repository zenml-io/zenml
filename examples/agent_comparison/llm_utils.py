"""LLM Utility Functions.

This module provides utilities for LLM integration using LiteLLM
with smart fallbacks when API keys are not available.
"""

import os

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


def call_llm(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Call LLM using LiteLLM with fallback to mock response.

    Args:
        prompt: The prompt to send to the LLM
        model: The model to use (defaults to gpt-3.5-turbo)

    Returns:
        LLM response text
    """
    if not should_use_real_llm():
        # Fallback to mock response
        return f"Mock response for: {prompt[:50]}..."

    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return (
            response.choices[0].message.content
            or f"Empty response for: {prompt[:50]}..."
        )
    except Exception as e:
        logger.warning(f"LLM call failed: {e}. Falling back to mock response.")
        return f"Fallback response for: {prompt[:50]}..."
