"""Local terminal input helpers for dynamic pipeline wait conditions."""

import json
import select
import sys
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Optional, Tuple

from zenml.client import Client
from zenml.models import (
    RunWaitConditionResolution,
    RunWaitConditionResolveRequest,
    RunWaitConditionResponse,
)

if TYPE_CHECKING:
    from zenml.orchestrators import BaseOrchestrator


def can_answer_wait_condition_interactively(
    orchestrator: "BaseOrchestrator",
) -> bool:
    """Check whether a wait condition can be answered interactively.

    Args:
        orchestrator: The orchestrator running the dynamic pipeline.

    Returns:
        Whether terminal prompting should be enabled for the current process.
    """
    from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator

    return bool(
        isinstance(orchestrator, LocalOrchestrator)
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )


def print_wait_condition_details(
    condition: "RunWaitConditionResponse",
) -> None:
    """Print wait-condition details for interactive terminal input.

    Args:
        condition: The wait condition shown to the user.
    """
    print()
    print("Waiting for input.")
    print(f"Question: {condition.question or 'Please provide input.'}")
    if condition.data_schema is not None:
        print("Expected JSON schema:")
        print(json.dumps(condition.data_schema, indent=2, sort_keys=True))
    print("Press Enter on an empty line to submit null.")
    print("Press Ctrl+C to abort.")
    print("> ", end="", flush=True)


@contextmanager
def maybe_enable_interactive_wait_prompt(
    orchestrator: "BaseOrchestrator",
    condition: "RunWaitConditionResponse",
) -> Iterator[bool]:
    """Render and clean up the terminal prompt for interactive waiting.

    Args:
        orchestrator: The orchestrator running the dynamic pipeline.
        condition: The wait condition shown to the user.

    Yields:
        Whether interactive input is enabled.
    """
    enabled = can_answer_wait_condition_interactively(orchestrator)
    if not enabled:
        yield False
        return

    print_wait_condition_details(condition=condition)
    try:
        yield True
    finally:
        print()


def read_stdin_line_with_timeout(
    timeout: float,
) -> Tuple[bool, Optional[str]]:
    """Read a line from stdin with a timeout.

    Args:
        timeout: Maximum number of seconds to wait.

    Returns:
        A tuple indicating whether input was received and the entered value.
        Empty input is returned as an empty string.
    """
    if timeout <= 0:
        return False, None

    try:
        readable, _, _ = select.select([sys.stdin], [], [], timeout)
    except (AttributeError, OSError, ValueError):
        # If readiness checks are unavailable, we can at least wait for the
        # same timeout window before attempting a direct read.
        time.sleep(timeout)
    else:
        if not readable:
            return False, None

    raw_value = sys.stdin.readline()
    if raw_value == "":
        return False, None

    return True, raw_value.rstrip("\n")


def poll_interactive_wait_condition_input(
    condition: "RunWaitConditionResponse",
    poll_interval: int,
) -> None:
    """Poll interactive input for a wait condition.

    Args:
        condition: The wait condition to resolve.
        poll_interval: Maximum number of seconds to wait.
    """
    has_input, raw_value = read_stdin_line_with_timeout(
        timeout=float(poll_interval),
    )
    if not has_input:
        return

    result: Optional[Any] = None

    if raw_value:
        if condition.data_schema is not None:
            try:
                result = json.loads(raw_value)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON input: {e}")
                print("> ", end="", flush=True)
                return
        else:
            result = raw_value

    try:
        Client().zen_store.resolve_run_wait_condition(
            run_wait_condition_id=condition.id,
            resolve_request=RunWaitConditionResolveRequest(
                resolution=RunWaitConditionResolution.CONTINUE,
                result=result,
            ),
        )
    except Exception as e:
        print(f"Failed to resolve wait condition: {e}")
        print("> ", end="", flush=True)
        return
