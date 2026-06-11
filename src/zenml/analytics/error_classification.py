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
"""Privacy-safe classification of exceptions for analytics.

This module turns a raw exception into a small set of *structured, non-PII*
labels (category, origin, fingerprint) that make failures diagnosable in
aggregate WITHOUT ever transmitting user content.

Privacy guarantees:
  * The exception **message** and **traceback text are never read or sent**.
    Classification is based solely on the exception *type* and on the
    *module/function names* of stack frames in ZenML and installed packages.
  * User stack frames are reduced to the single label ``"user_code"`` -- their
    file paths (which may contain usernames/paths) and function names are
    never included anywhere, including in the fingerprint.
  * All outputs are drawn from a fixed, closed vocabulary (categories/origins)
    or are one-way SHA-256 hashes, so no free text can leak.
"""

import hashlib
import os
import traceback
from typing import Any, Dict, List, Optional

# --- closed vocabularies (no free text ever leaves the machine) -------------

CATEGORY_USER_CODE = "user_code"
CATEGORY_CONFIG = "config"
CATEGORY_AUTH = "auth"
CATEGORY_CONNECTIVITY = "connectivity"
CATEGORY_RESOURCE = "resource"
CATEGORY_INTEGRATION = "integration"
CATEGORY_PLATFORM = "platform"
CATEGORY_UNKNOWN = "unknown"

ORIGIN_USER_CODE = "user_code"
ORIGIN_INTEGRATION = "integration"
ORIGIN_PLATFORM = "platform"
ORIGIN_UNKNOWN = "unknown"

# Third-party exception *class names* (safe: a class name is not user data)
# that reliably indicate connectivity / auth problems. Matched against the
# whole MRO so subclasses are caught too.
_CONNECTIVITY_NAMES = frozenset(
    {
        "ConnectionError",
        "ConnectTimeout",
        "ConnectTimeoutError",
        "ReadTimeout",
        "ReadTimeoutError",
        "Timeout",
        "EndpointConnectionError",
        "ServerSelectionTimeoutError",
        "NewConnectionError",
        "MaxRetryError",
        "SSLError",
        "ProtocolError",
        "ConnectionResetError",
        "ConnectionRefusedError",
        "NetworkError",
    }
)
_AUTH_NAMES = frozenset(
    {
        "NoCredentialsError",
        "PartialCredentialsError",
        "DefaultCredentialsError",
        "CredentialsError",
        "RefreshError",
        "Unauthorized",
        "Forbidden",
        "AccessDenied",
        "AuthenticationError",
        "AuthorizationError",
        "InvalidToken",
        "TokenExpiredError",
    }
)
_RESOURCE_NAMES = frozenset(
    {
        "OutOfMemoryError",
        "ResourceExhausted",
        "ResourceExhaustedError",
        "OOMKilled",
    }
)


def _mro_names(exc_type: type) -> List[str]:
    """Return the class names in an exception's MRO (safe, no user data).

    Args:
        exc_type: The exception class.

    Returns:
        The list of class names in the method resolution order.
    """
    names = []
    try:
        for klass in exc_type.__mro__:
            names.append(klass.__name__)
    except Exception:
        names.append(getattr(exc_type, "__name__", "Unknown"))
    return names


def _zenml_root() -> str:
    """Best-effort absolute path of the installed ``zenml`` package.

    Returns:
        The package directory, or the string ``"zenml"`` as a fallback token.
    """
    try:
        import zenml

        f = getattr(zenml, "__file__", None)
        if f:
            return os.path.dirname(os.path.abspath(f))
    except Exception:
        pass
    return "zenml"


def _frame_origin(filename: str, zenml_root: str) -> str:
    """Classify a single stack frame's origin from its filename only.

    Args:
        filename: The frame's file path.
        zenml_root: The installed zenml package directory.

    Returns:
        One of the ORIGIN_* constants.
    """
    fn = filename or ""
    norm = fn.replace("\\", "/")
    if zenml_root and os.path.abspath(fn).startswith(zenml_root):
        return ORIGIN_PLATFORM
    if "/site-packages/zenml/" in norm or "/zenml/src/zenml/" in norm:
        return ORIGIN_PLATFORM
    if "site-packages" in norm or "dist-packages" in norm:
        return ORIGIN_INTEGRATION
    return ORIGIN_USER_CODE


def _safe_frame_token(filename: str, func: str) -> str:
    """Build a non-PII fingerprint token for a ZenML/library frame.

    Uses only the file's *basename* and the function name -- never the full
    path (which can contain usernames). Callers must exclude user frames
    before calling this.

    Args:
        filename: The frame's file path.
        func: The frame's function name.

    Returns:
        A short ``"module:func"`` token.
    """
    base = os.path.basename(filename or "")
    return f"{base}:{func or ''}"


def classify_error(
    exc_type: Optional[type],
    exc_value: Optional[BaseException],
    exc_tb: Optional[Any],
) -> Dict[str, str]:
    """Classify an exception into privacy-safe analytics labels.

    Args:
        exc_type: The exception class (``type_`` from ``__exit__``).
        exc_value: The exception instance (unused for content; kept for API
            symmetry and possible isinstance checks).
        exc_tb: The traceback object.

    Returns:
        A dict with ``error_category``, ``error_origin`` and
        ``error_fingerprint``. Returns an empty dict if there is no exception
        or if classification fails for any reason (it must never raise).
    """
    if exc_type is None:
        return {}

    try:
        # Lazy import so this module stays import-cheap and dependency-light.
        from zenml.exceptions import (
            AuthorizationException,
            ZenMLBaseException,
        )

        mro = set(_mro_names(exc_type))
        zenml_root = _zenml_root()

        # --- origin: where (deepest frame) was the exception raised? --------
        frames = []
        try:
            frames = traceback.extract_tb(exc_tb) if exc_tb is not None else []
        except Exception:
            frames = []

        origin = ORIGIN_UNKNOWN
        if frames:
            origin = _frame_origin(frames[-1].filename, zenml_root)

        # --- category: prefer exception-type signal, else fall back to origin
        category = CATEGORY_UNKNOWN
        if isinstance(exc_value, AuthorizationException) or (
            mro & _AUTH_NAMES
        ):
            category = CATEGORY_AUTH
        elif isinstance(exc_value, (PermissionError,)) and not (
            mro & _CONNECTIVITY_NAMES
        ):
            category = CATEGORY_AUTH
        elif mro & _CONNECTIVITY_NAMES or isinstance(
            exc_value, (ConnectionError, TimeoutError)
        ):
            category = CATEGORY_CONNECTIVITY
        elif mro & _RESOURCE_NAMES or isinstance(exc_value, MemoryError):
            category = CATEGORY_RESOURCE
        elif isinstance(exc_value, ZenMLBaseException):
            # ZenML's own exceptions are configuration / usage problems,
            # not platform bugs (those surface as non-ZenML exceptions
            # raised from within zenml frames).
            category = CATEGORY_CONFIG
        elif origin == ORIGIN_USER_CODE:
            category = CATEGORY_USER_CODE
        elif origin == ORIGIN_PLATFORM:
            category = CATEGORY_PLATFORM
        elif origin == ORIGIN_INTEGRATION:
            category = CATEGORY_INTEGRATION

        # --- fingerprint: class name + ZenML/library frame tokens only ------
        # User frames are excluded entirely (no paths, no funcs, no message).
        tokens = [exc_type.__name__]
        for fr in frames:
            if _frame_origin(fr.filename, zenml_root) != ORIGIN_USER_CODE:
                tokens.append(_safe_frame_token(fr.filename, fr.name))
        fingerprint = hashlib.sha256(
            "|".join(tokens).encode("utf-8", "ignore")
        ).hexdigest()[:16]

        return {
            "error_category": category,
            "error_origin": origin,
            "error_fingerprint": fingerprint,
        }
    except Exception:
        # Classification must never interfere with the run or the event.
        return {}
