#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""ZenML Step HeartBeat functionality."""

import _thread
import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from zenml.enums import ExecutionStatus
from zenml.utils.time_utils import to_utc_timezone

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StepHeartBeatTerminationException(Exception):
    """Custom exception class for heartbeat termination."""

    pass


class StepHeartbeatWorker:
    """Worker class implementing heartbeat polling and remote termination."""

    STEP_HEARTBEAT_INTERVAL_SECONDS = 60

    def __init__(self, step_id: UUID):
        """Heartbeat worker constructor.

        Args:
            step_id: The step id heartbeat is running for.
        """
        self._step_id = step_id

        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._terminated: bool = False

    # properties

    @property
    def is_running(self) -> bool:
        """Property function for running signal.

        Returns:
            True if the worker is running.
        """
        return self._running

    @property
    def is_terminated(self) -> bool:
        """Property function for termination signal.

        Returns:
            True if the worker has been terminated.
        """
        return self._terminated

    @property
    def interval(self) -> int:
        """Property function for heartbeat interval.

        Returns:
            The heartbeat polling interval value.
        """
        return self.STEP_HEARTBEAT_INTERVAL_SECONDS

    @property
    def name(self) -> str:
        """Property function for heartbeat worker name.

        Returns:
            The name of the heartbeat worker.
        """
        return f"HeartBeatWorker-{self.step_id}"

    @property
    def step_id(self) -> UUID:
        """Property function for heartbeat worker step ID.

        Returns:
            The id of the step heartbeat is running for.
        """
        return self._step_id

    # public functions

    def start(self) -> None:
        """Start the heartbeat worker on a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._running = True
        self._terminated = False
        self._thread = threading.Thread(
            target=self._run, name=self.name, daemon=True
        )
        self._thread.start()
        logger.debug(
            "Daemon thread %s started (interval=%s)", self.name, self.interval
        )

    def stop(self) -> None:
        """Stops the heartbeat worker."""
        if not self._running:
            return
        self._running = False
        logger.debug("%s stop requested", self.name)

    def is_alive(self) -> bool:
        """Liveness of the heartbeat worker thread.

        Returns:
            True if the heartbeat worker thread is alive, False otherwise.
        """
        t = self._thread
        return bool(t and t.is_alive())

    def _run(self) -> None:
        logger.debug("%s run() loop entered", self.name)
        try:
            while self._running:
                try:
                    self._heartbeat()
                    # One-shot: signal the main thread and stop the loop.
                    if self._terminated:
                        logger.info(
                            "%s is remotely stopped, interrupting main thread",
                            self.name,
                        )
                        _thread.interrupt_main()  # raises KeyboardInterrupt in main thread
                        self._running = False
                    # Ensure we stop our own loop as well.

                except Exception as exc:
                    # Log-and-continue policy for all other errors.
                    logger.debug(
                        "%s heartbeat() failed with %s", self.name, str(exc)
                    )
                # Sleep after each attempt (even after errors, unless stopped).
                if self._running:
                    time.sleep(self.interval)
        finally:
            logger.debug("%s run() loop exiting", self.name)

    def _heartbeat(self) -> None:
        from zenml.config.global_config import GlobalConfiguration

        store = GlobalConfiguration().zen_store

        response = store.update_step_heartbeat(step_run_id=self.step_id)

        if response.pipeline_run_status in {
            ExecutionStatus.STOPPED,
            ExecutionStatus.STOPPING,
        }:
            self._terminated = True


def is_heartbeat_unhealthy(
    step_run_id: UUID,
    status: ExecutionStatus,
    latest_heartbeat: datetime | None,
    start_time: datetime | None = None,
    heartbeat_threshold: int | None = None,
) -> bool:
    """Utility function - Checks if step heartbeats indicate un-healthy execution.

    Args:
        step_run_id: The run step id.
        status: The run step status.
        latest_heartbeat: The run step latest heartbeat.
        start_time: The run step start time.
        heartbeat_threshold: If heartbeat enabled the max minutes without heartbeat
            for healthy, running tasks.

    Returns:
        True if the step heartbeat is unhealthy, False otherwise.
    """
    if not heartbeat_threshold:
        return False

    if status.is_finished:
        return False

    if latest_heartbeat:
        heartbeat_diff = datetime.now(tz=timezone.utc) - to_utc_timezone(
            latest_heartbeat
        )
    elif start_time:
        heartbeat_diff = datetime.now(tz=timezone.utc) - to_utc_timezone(
            start_time
        )
    else:
        return False

    logger.debug("Step %s heartbeat diff=%s", step_run_id, heartbeat_diff)

    if heartbeat_diff.total_seconds() > heartbeat_threshold * 60:
        return True

    return False
