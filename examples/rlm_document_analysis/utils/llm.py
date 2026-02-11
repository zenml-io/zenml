# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
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
"""Thin LLM wrapper with OpenAI-compatible API and fallback mode."""

import logging
import os
import random
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_llm_unavailable_warning_shown = False


def llm_available() -> bool:
    """Check if an OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _get_model() -> str:
    """Get the configured LLM model name."""
    return os.getenv("LLM_MODEL", "gpt-4o-mini")


def _get_client() -> Any:
    """Lazy-import and instantiate the OpenAI client."""
    from openai import OpenAI

    return OpenAI()


def llm_call(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    json_mode: bool = False,
    max_retries: int = 3,
) -> str:
    """Make a single LLM call with retry and exponential backoff.

    Args:
        system: System prompt.
        user: User prompt.
        model: Model name override.
        json_mode: If True, request JSON response format.
        max_retries: Maximum retry attempts for transient errors.

    Returns:
        Response text, or empty string if unavailable/failed.
    """
    global _llm_unavailable_warning_shown

    if not llm_available():
        if not _llm_unavailable_warning_shown:
            logger.warning(
                "OPENAI_API_KEY not set. Using keyword fallback mode. "
                "Set OPENAI_API_KEY for full LLM-powered analysis."
            )
            _llm_unavailable_warning_shown = True
        return ""

    model = model or _get_model()
    client = _get_client()

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            if attempt == max_retries:
                logger.warning(
                    "LLM call failed after %d attempts: %s",
                    max_retries + 1,
                    e,
                )
                return ""
            delay = min(8.0, 0.5 * (2**attempt)) * random.uniform(0.8, 1.2)
            logger.info(
                "LLM call attempt %d failed, retrying in %.1fs: %s",
                attempt + 1,
                delay,
                e,
            )
            time.sleep(delay)

    return ""
