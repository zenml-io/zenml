"""Invocation lifecycle state for dynamic pipeline execution."""

from __future__ import annotations

import threading
from concurrent.futures import Future
from enum import Enum, auto
from typing import Optional

from zenml.models import StepRunResponse


class _InvocationLifecycleState(Enum):
    """Lifecycle states for a dynamic step invocation."""

    WAITING = auto()
    DISPATCHED = auto()
    FINISHED_SUCCESS = auto()
    FINISHED_FAILURE = auto()


class InvocationState:
    """Mutable lifecycle state for a single step invocation."""

    def __init__(self, invocation_id: str) -> None:
        """Initialize the invocation state.

        Args:
            invocation_id: The invocation ID of the step.
        """
        self.invocation_id = invocation_id
        self._condition = threading.Condition()
        self._lifecycle_state = _InvocationLifecycleState.WAITING
        self._was_dispatched = False
        self._inline_future: Optional[Future["StepRunResponse"]] = None
        self._terminal_step_run: Optional["StepRunResponse"] = None
        self._terminal_exception: Optional[BaseException] = None

    def _assert_can_transition(
        self,
        *,
        event: str,
        allowed_from: set[_InvocationLifecycleState],
        requires_inline_future: Optional[bool] = None,
    ) -> None:
        """Validate that a lifecycle transition is allowed.

        Args:
            event: The lifecycle transition event.
            allowed_from: The lifecycle states that allow this event.
            requires_inline_future: Whether the event requires an inline future.

        Raises:
            RuntimeError: If the transition is invalid.
        """
        if self._lifecycle_state not in allowed_from:
            raise RuntimeError(
                f"Invalid invocation state transition `{event}` for "
                f"`{self.invocation_id}` from `{self._lifecycle_state.name}`."
            )

        has_inline_future = self._inline_future is not None
        if requires_inline_future is not None and (
            has_inline_future != requires_inline_future
        ):
            raise RuntimeError(
                f"Invalid invocation state transition `{event}` for "
                f"`{self.invocation_id}` with "
                f"`has_inline_future={has_inline_future}`."
            )

    def bind_inline_future(self, future: Future["StepRunResponse"]) -> None:
        """Bind the executor future of an inline step.

        Args:
            future: The executor future of the inline step execution.
        """
        with self._condition:
            self._assert_can_transition(
                event="bind_inline_future",
                allowed_from={_InvocationLifecycleState.WAITING},
                requires_inline_future=False,
            )
            self._inline_future = future
            self._was_dispatched = True
            self._lifecycle_state = _InvocationLifecycleState.DISPATCHED
            self._condition.notify_all()

    def mark_dispatched(self) -> None:
        """Mark the invocation as dispatched."""
        with self._condition:
            self._assert_can_transition(
                event="mark_dispatched",
                allowed_from={_InvocationLifecycleState.WAITING},
                requires_inline_future=False,
            )
            self._was_dispatched = True
            self._lifecycle_state = _InvocationLifecycleState.DISPATCHED
            self._condition.notify_all()

    def mark_success(self, step_run: "StepRunResponse") -> None:
        """Mark the invocation as successfully finished.

        Args:
            step_run: The terminal step run.
        """
        with self._condition:
            self._assert_can_transition(
                event="mark_success",
                allowed_from={
                    _InvocationLifecycleState.WAITING,
                    _InvocationLifecycleState.DISPATCHED,
                },
            )
            self._terminal_step_run = step_run
            self._lifecycle_state = _InvocationLifecycleState.FINISHED_SUCCESS
            self._condition.notify_all()

    def mark_failure(self, exception: BaseException) -> None:
        """Mark the invocation as failed.

        Args:
            exception: The terminal exception of the invocation.
        """
        with self._condition:
            self._assert_can_transition(
                event="mark_failure",
                allowed_from={
                    _InvocationLifecycleState.WAITING,
                    _InvocationLifecycleState.DISPATCHED,
                },
            )
            self._terminal_exception = exception
            self._lifecycle_state = _InvocationLifecycleState.FINISHED_FAILURE
            self._condition.notify_all()

    def inline_future(self) -> Optional[Future["StepRunResponse"]]:
        """Get the executor future of an inline step if available.

        Returns:
            The executor future if it was bound.
        """
        with self._condition:
            return self._inline_future

    def is_dispatched(self) -> bool:
        """Check whether the invocation was dispatched.

        Returns:
            Whether the invocation was dispatched.
        """
        with self._condition:
            return self._was_dispatched

    def is_terminal(self) -> bool:
        """Check whether the invocation reached a terminal state.

        Returns:
            Whether the invocation reached a terminal state.
        """
        with self._condition:
            return (
                self._lifecycle_state == _InvocationLifecycleState.FINISHED_SUCCESS
                or self._lifecycle_state
                == _InvocationLifecycleState.FINISHED_FAILURE
            )

    def terminal_exception(self) -> Optional[BaseException]:
        """Get the terminal exception if one exists.

        Returns:
            The terminal exception if one exists.
        """
        with self._condition:
            return self._terminal_exception

    def wait_for_inline_future_or_terminal(
        self,
    ) -> Optional[Future["StepRunResponse"]]:
        """Wait for an inline executor future or terminal pre-dispatch state.

        Returns:
            The inline executor future if it was bound, otherwise `None` if the
            invocation reached a terminal state before inline execution started.
        """
        with self._condition:
            while (
                self._inline_future is None
                and self._terminal_step_run is None
                and self._terminal_exception is None
            ):
                self._condition.wait()

            return self._inline_future

    def wait_for_dispatch_or_terminal(self) -> bool:
        """Wait for dispatch or terminal pre-dispatch state.

        Returns:
            Whether the invocation was dispatched.
        """
        with self._condition:
            while (
                not self._was_dispatched
                and self._terminal_step_run is None
                and self._terminal_exception is None
            ):
                self._condition.wait()

            return self._was_dispatched

    def wait_for_terminal_step_run(self) -> "StepRunResponse":
        """Wait for the invocation to reach a terminal state.

        # noqa: DAR401
        Raises:
            BaseException: The terminal exception of the invocation.

        Returns:
            The successful terminal step run.
        """
        with self._condition:
            while (
                self._terminal_step_run is None
                and self._terminal_exception is None
            ):
                self._condition.wait()

            if self._terminal_exception is not None:
                raise self._terminal_exception

            assert self._terminal_step_run is not None
            return self._terminal_step_run
