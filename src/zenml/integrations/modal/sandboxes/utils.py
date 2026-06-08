#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Helpers for the Modal sandbox flavor."""

from typing import TYPE_CHECKING, Any, Iterable, Iterator, Optional

if TYPE_CHECKING:
    import modal


def normalize_optional_config_value(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and return None for empty strings.

    Args:
        value: The raw config value.

    Returns:
        Stripped non-empty string, or ``None``.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def line_buffer(chunks: Iterable[Any]) -> Iterator[str]:
    """Re-emit byte/str chunks one decoded line at a time.

    Modal returns LogsReader iterables that yield byte chunks, not lines,
    so callers line-buffer on this side to match the line-delimited
    ``SandboxProcess.stdout()`` / ``stderr()`` contract.

    Args:
        chunks: Source iterable yielding bytes, str, or None.

    Yields:
        Lines with trailing newline when present; a final newline-less
        remainder is yielded once the source is exhausted.
    """
    buffer = ""
    for chunk in chunks:
        if chunk is None:
            continue
        if isinstance(chunk, bytes):
            text = chunk.decode("utf-8", errors="replace")
        else:
            text = str(chunk)
        buffer += text
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield line + "\n"
    if buffer:
        yield buffer


def build_modal_image(
    image_uri: str, registry_secret: Optional[Any] = None
) -> "modal.Image":
    """Wrap ``modal.Image.from_registry`` with an optional registry secret.

    Args:
        image_uri: Registry reference, e.g. ``python:3.11-slim``.
        registry_secret: Optional ``modal.Secret`` carrying registry
            credentials; passed through when present.

    Returns:
        A ``modal.Image`` instance ready to pass to ``Sandbox.create``.
    """
    import modal

    if registry_secret is not None:
        return modal.Image.from_registry(image_uri, secret=registry_secret)
    return modal.Image.from_registry(image_uri)
