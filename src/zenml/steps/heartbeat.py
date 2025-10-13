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
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, conint, model_validator

from zenml.enums import ExecutionStatus

logger = logging.getLogger(__name__)


class StepHeartBeatTerminationException(Exception):
    """Custom exception class for heartbeat termination."""

    pass


class StepHeartBeatOptions(BaseModel):
    """Options group for step heartbeat execution."""

    step_id: UUID
    interval: Annotated[int, conint(ge=10, le=60)]
    name: str | None = None

    @model_validator(mode="after")
    def set_default_name(self) -> "StepHeartBeatOptions":
        """Model validator - set name value if missing.

        Returns:
            The validated step heartbeat options.
        """
        if not self.name:
            self.name = f"HeartBeatWorker-{self.step_id}"

        return self


class HeartbeatWorker:
    """Worker class implementing heartbeat polling and remote termination."""

    def __init__(self, options: StepHeartBeatOptions):
        """Heartbeat worker constructor.

        Args:
            options: Parameter group - polling interval, step id, etc.
        """
        self.options = options

        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._terminated: bool = (
            False  # one-shot guard to avoid repeated interrupts
        )

    # properties

    @property
    def interval(self) -> int:
        """Property function for heartbeat interval.

        Returns:
            The heartbeat polling interval value.
        """
        return self.options.interval

    @property
    def name(self) -> str:
        """Property function for heartbeat worker name.

        Returns:
            The name of the heartbeat worker.
        """
        return str(self.options.name)

    @property
    def step_id(self) -> UUID:
        """Property function for heartbeat worker step ID.

        Returns:
            The id of the step heartbeat is running for.
        """
        return self.options.step_id

    # public functions

    def start(self) -> None:
        """Start the heartbeat worker on a background thread."""
        if self._thread and self._thread.is_alive():
            logger.info("%s already running; start() is a no-op", self.name)
            return

        self._running = True
        self._terminated = False
        self._thread = threading.Thread(
            target=self._run, name=self.name, daemon=True
        )
        self._thread.start()
        logger.info(
            "Daemon thread %s started (interval=%s)", self.name, self.interval
        )

    def stop(self) -> None:
        """Stops the heartbeat worker."""
        if not self._running:
            return
        self._running = False
        logger.info("%s stop requested", self.name)

    def is_alive(self) -> bool:
        """Liveness of the heartbeat worker thread.

        Returns:
            True if the heartbeat worker thread is alive, False otherwise.
        """
        t = self._thread
        return bool(t and t.is_alive())

    def _run(self) -> None:
        logger.info("%s run() loop entered", self.name)
        try:
            while self._running:
                try:
                    self._heartbeat()
                except StepHeartBeatTerminationException:
                    # One-shot: signal the main thread and stop the loop.
                    if not self._terminated:
                        self._terminated = True
                        logger.info(
                            "%s received HeartBeatTerminationException; "
                            "interrupting main thread",
                            self.name,
                        )
                        _thread.interrupt_main()  # raises KeyboardInterrupt in main thread
                    # Ensure we stop our own loop as well.
                    self._running = False
                except Exception:
                    # Log-and-continue policy for all other errors.
                    logger.exception(
                        "%s heartbeat() failed; continuing", self.name
                    )
                # Sleep after each attempt (even after errors, unless stopped).
                if self._running:
                    time.sleep(self.interval)
        finally:
            logger.info("%s run() loop exiting", self.name)

    def _heartbeat(self) -> None:
        from zenml.config.global_config import GlobalConfiguration

        store = GlobalConfiguration().zen_store

        response = store.update_step_heartbeat(step_run_id=self.step_id)

        if response.status in {
            ExecutionStatus.STOPPED,
            ExecutionStatus.STOPPING,
        }:
            raise StepHeartBeatTerminationException(
                f"Step {self.step_id} remotely stopped with status {response.status}."
            )
