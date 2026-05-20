"""Local terminal input helpers for dynamic pipeline wait conditions."""

import json
import select
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Optional, Tuple

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_DISABLE_INTERACTIVE_INPUT,
    handle_bool_env_var,
)
from zenml.enums import RunWaitConditionResolution
from zenml.models import (
    RunWaitConditionResolveRequest,
    RunWaitConditionResponse,
)
from zenml.utils.json_utils import parse_value_for_schema

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

    try:
        # We use select to check if stdin is ready to be read. If it isn't
        # available on the current platform, we don't support interactive input.
        select.select([sys.stdin], [], [], 0)
    except (AttributeError, OSError, ValueError):
        return False

    return bool(
        not handle_bool_env_var(
            ENV_ZENML_DISABLE_INTERACTIVE_INPUT, default=False
        )
        and isinstance(orchestrator, LocalOrchestrator)
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
    # Keep the logs neutral because they're printed as-is also in Kitaru.
    print()
    if condition.data_schema is not None:
        print("Waiting for input.")
    else:
        print("Waiting for confirmation.")
    print(f"Question: {condition.question or 'Please provide input.'}")
    if condition.data_schema is not None:
        print("Expected JSON schema:")
        print(json.dumps(condition.data_schema, indent=2, sort_keys=True))
        print("Press Enter on an empty line to submit null.")
    else:
        print("Press Enter to continue.")
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
        return False, None

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
                result = parse_value_for_schema(
                    raw_value, condition.data_schema
                )
            except ValueError as e:
                print(f"Invalid input: {e}")
                print("> ", end="", flush=True)
                return

    try:
        Client().zen_store.resolve_run_wait_condition(
            run_wait_condition_id=condition.id,
            resolve_request=RunWaitConditionResolveRequest(
                resolution=RunWaitConditionResolution.CONTINUE,
                result=result,
            ),
        )
    except Exception as e:
        print(f"Failed to resolve: {e}")
        print("> ", end="", flush=True)
        return
