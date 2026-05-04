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
"""Step execution signal handler."""

import signal
import threading
from types import FrameType
from typing import Any, Dict, Optional

from typing_extensions import Self

from zenml.client import Client
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.exceptions import RunInterruptedException, RunStoppedException
from zenml.logger import get_logger
from zenml.models import StepRunResponse
from zenml.orchestrators import publish_utils
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

_SIGNALS = (signal.SIGTERM, signal.SIGINT)


class SignalHandler:
    """Handles signals during step execution.

    Only registers when called from the main thread — Python only delivers
    signals to the main thread, so we cannot interrupt steps running on worker
    threads.

    Usage:
        >>> handler = SignalHandler(step_run=step_run, execution_mode=mode)
        >>> handler.register()
        >>> try:
        ...     run_step()
        ... finally:
        ...     handler.unregister()

    Or as a context manager:
        >>> with SignalHandler(step_run=step_run, execution_mode=mode):
        ...     run_step()
    """

    def __init__(
        self,
        step_run: StepRunResponse,
        execution_mode: ExecutionMode,
    ) -> None:
        """Initialize the signal handler.

        Args:
            step_run: The step run to mark as stopped on interruption.
            execution_mode: The pipeline execution mode.
        """
        self._step_run = step_run
        self._execution_mode = execution_mode
        self._previous: Dict[int, Any] = {}

    def register(self) -> Self:
        """Install the handler.

        No-ops when called outside the main thread.

        Returns:
            Self.
        """
        if threading.current_thread() is not threading.main_thread():
            logger.debug(
                "Signal handler registration for step `%s` skipped because it "
                "was called from a non-main thread.",
                self._step_run.name,
            )
            return self

        if self._previous:
            return self
        for sig in _SIGNALS:
            self._previous[sig] = signal.signal(sig, self._handle)
        return self

    def unregister(self) -> None:
        """Restore the previously installed handlers."""
        if not self._previous:
            return
        for sig, prev in self._previous.items():
            signal.signal(sig, prev)
        self._previous.clear()

    def __enter__(self) -> Self:
        """Register on context entry.

        Returns:
            Self.
        """
        return self.register()

    def __exit__(self, *_: Any) -> None:
        """Unregister on context exit."""
        self.unregister()

    def _handle(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle a signal.

        Args:
            signum: The signal number.
            frame: The current stack frame.

        Raises:
            BaseException: Exception depending on the run/step status.
        """  # noqa: DOC503
        logger.info(
            f"Received signal {signum}. Requesting shutdown for step run "
            f"`{self._step_run.name}`..."
        )
        try:
            raise self._finalize_shutdown()
        finally:
            prev = self._previous.get(signum)
            if callable(prev):
                try:
                    prev(signum, frame)
                except Exception:
                    logger.exception(
                        f"Previous signal handler raised for signal {signum}."
                    )

    def _finalize_shutdown(self) -> BaseException:
        """Finalize the shutdown process.

        This method potentially publishes a stopped status and returns an
        exception to raise.

        Returns:
            The exception to raise.
        """
        try:
            client = Client()
            pipeline_run = client.get_pipeline_run(
                self._step_run.pipeline_run_id, hydrate=False
            )

            if pipeline_run.status in (
                ExecutionStatus.STOPPING,
                ExecutionStatus.STOPPED,
            ):
                publish_utils.publish_step_run_status_update(
                    step_run_id=self._step_run.id,
                    status=ExecutionStatus.STOPPED,
                    end_time=utc_now(),
                )
                return RunStoppedException("Pipeline run is stopped.")

            step_run = client.get_run_step(self._step_run.id, hydrate=False)

            if (
                pipeline_run.status == ExecutionStatus.FAILED
                and step_run.status == ExecutionStatus.RUNNING
                and self._execution_mode == ExecutionMode.FAIL_FAST
            ):
                publish_utils.publish_step_run_status_update(
                    step_run_id=self._step_run.id,
                    status=ExecutionStatus.STOPPED,
                    end_time=utc_now(),
                )
                return RunStoppedException(
                    "Step run was stopped due to a failure in the pipeline "
                    "run and the execution mode 'FAIL_FAST'."
                )

            if step_run.status == ExecutionStatus.STOPPING:
                publish_utils.publish_step_run_status_update(
                    step_run_id=step_run.id,
                    status=ExecutionStatus.STOPPED,
                    end_time=utc_now(),
                )
                return RunStoppedException("Pipeline run is stopped.")

            return RunInterruptedException("The execution was interrupted.")
        except Exception as e:
            return RunInterruptedException(str(e))
