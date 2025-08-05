"""API utilities for LLM providers."""

import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI


def setup_openai_client() -> OpenAI:
    """Set up OpenAI client with API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required. "
            "Get your API key from https://platform.openai.com/api-keys"
        )
    try:
        return OpenAI(api_key=api_key)
    except TypeError as e:
        if "proxies" in str(e):
            # Try with minimal config to avoid version issues
            return OpenAI(
                api_key=api_key,
                base_url="https://api.openai.com/v1"
            )
        raise


def call_openai_api(
    prompt: str,
    model: str = "gpt-4",
    temperature: float = 0.1,
    max_tokens: int = 2000,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call OpenAI API with retry logic."""
    client = setup_openai_client()

    for attempt in range(max_retries):
        try:
            start_time = time.time()

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            end_time = time.time()

            return {
                "content": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "response_time_ms": int((end_time - start_time) * 1000),
                "finish_reason": response.choices[0].finish_reason,
            }

        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                print(
                    f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}"
                )
                time.sleep(wait_time)
                continue
            elif attempt < max_retries - 1:
                print(f"API error on attempt {attempt + 1}: {e}")
                time.sleep(1)
                continue
            raise e

    raise Exception(f"Failed to get response after {max_retries} attempts")


def parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling common formatting issues."""
    if not response_text:
        return None

    # Try direct JSON parsing first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text that might have extra content
    import re

    # Look for JSON blocks
    json_pattern = r"```json\s*(.*?)\s*```"
    match = re.search(json_pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Look for any JSON-like structure
    brace_pattern = r"\{.*\}"
    match = re.search(brace_pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def estimate_token_cost(usage: Dict[str, Any], model: str = "gpt-4") -> float:
    """Estimate API cost based on token usage."""
    # Approximate pricing (as of 2024 - check current pricing)
    pricing = {
        "gpt-4": {
            "prompt": 0.03 / 1000,  # $0.03 per 1K prompt tokens
            "completion": 0.06 / 1000,  # $0.06 per 1K completion tokens
        },
        "gpt-3.5-turbo": {
            "prompt": 0.0015 / 1000,  # $0.0015 per 1K prompt tokens
            "completion": 0.002 / 1000,  # $0.002 per 1K completion tokens
        },
    }

    if model not in pricing:
        model = "gpt-4"  # Default to GPT-4 pricing

    prompt_cost = usage.get("prompt_tokens", 0) * pricing[model]["prompt"]
    completion_cost = (
        usage.get("completion_tokens", 0) * pricing[model]["completion"]
    )

    return prompt_cost + completion_cost


def validate_api_setup() -> bool:
    """Validate that API is properly configured."""
    try:
        client = setup_openai_client()

        # Make a simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'API test successful'"}
            ],
            max_tokens=10,
        )

        return "successful" in response.choices[0].message.content.lower()

    except Exception as e:
        print(f"API validation failed: {e}")
        return False
