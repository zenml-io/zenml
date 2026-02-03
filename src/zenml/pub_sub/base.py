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
"""Base abstractions for the pub/sub layer."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from zenml.pub_sub.models import (
    CriticalEvent,
    CriticalEventType,
    MessageEnvelope,
    MessagePayload,
)

logger = logging.getLogger(__name__)


class MessageDecodeError(Exception):
    """Raised when a raw broker message cannot be decoded/preprocessed."""


class MessageExecutionError(Exception):
    """Raised when message processing fails after retries."""


class MessageEncodeError(Exception):
    """Raised when a payload cannot be encoded into a broker message."""


class MessageSubmissionError(Exception):
    """Raised when sending a message fails."""


class ProducerConfig(BaseModel):
    """Config object grouping producer configuration params."""

    send_retries: int = 0


class ProducerBase(ABC):
    """Async producer base.

    Backends implement:
      1) build_message(payload) -> backend-specific message object (Any)
      2) send_message(message) -> submit to broker

    Base provides:
      - publish(payload): build + send (+ optional retries) and emits CriticalEvent on failure.
    """

    def __init__(self, config: ProducerConfig) -> None:
        """Producer constructor.

        Args:
            config: The producer config object.
        """
        self._cfg = config

    @property
    def config(self) -> ProducerConfig:
        """Implements the 'config' property.

        Returns:
            The producer config object.
        """
        return self._cfg

    @abstractmethod
    async def build_message(self, payload: MessagePayload) -> Any:
        """Convert the message to a broker-specific payload.

        Args:
            payload: A MessagePayload object.

        Returns:
            A broker-specific message.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message: Any) -> Any:
        """Sends a message to the broker.

        Args:
            message: A broker-specific message.

        Returns:
            A broker-specific response, most usually message ID.
        """
        raise NotImplementedError

    async def handle_critical_event(self, event: CriticalEvent) -> None:
        """Critical event handler.

        A critical event indicates that the application behavior has degraded.
        For instance, the inability to serialize the message to a broker-compatible format
        is extremely severe as it most probably repeats across messages meaning no messages
        are published for execution at all.

        A complete implementation of a critical event handling process would be the following:

        1. Log in detailed fashion the event so that it is traceable in the logs.
        2. Publish the event to an event aggregator service so that it is tracked long-term and
        alerts can be generated based on its frequency and severity.
        3. Hold the message in a DLQ to enable re-execution when a bug fix is introduced in the code.

        Args:
            event: A critical event instance.
        """
        # TODO: Extend with more tooling/operations.
        logger.error("Critical event handler received event: %s", event)

    async def publish(self, payload: MessagePayload) -> Any:
        """Build and send message, emitting CriticalEvent on failure.

        Args:
            payload: Application payload.

        Returns:
            Backend-specific send result/receipt.

        Raises:
            MessageEncodeError: If encoding/building fails.
            MessageSubmissionError: If sending fails after retries.
        """
        try:
            message = await self.build_message(payload)
        except Exception as exc:
            await self.handle_critical_event(
                CriticalEvent(
                    value=CriticalEventType.encode_failed,
                    description=f"Encode failed for payload {payload.id}: {exc!r}",
                    created_at=datetime.now(tz=timezone.utc),
                )
            )
            raise MessageEncodeError(
                f"Encode failed for payload {payload.id}"
            ) from exc

        attempts = self.config.send_retries + 1

        for attempt in range(attempts):
            try:
                return await self.send_message(message)
            except Exception as exc:
                logger.error(
                    "Attempt %s to send message %s failed with %s",
                    attempt,
                    payload.id,
                    exc,
                )

        await self.handle_critical_event(
            CriticalEvent(
                value=CriticalEventType.send_failed,
                description=f"Submission failed for payload {payload.id}",
                created_at=datetime.now(tz=timezone.utc),
            )
        )
        raise MessageSubmissionError(f"Send failed for payload {payload.id}")


class ConsumerRuntimeConfig(BaseModel):
    """Config shared by polling and push consumers."""

    late_ack: bool = True
    execution_retries: int = 0
    ack_retries: int = 3
    ack_retry_backoff: int = 1
    blocking_execution: bool = True


class Executor(ABC):
    """Abstract executor interface."""

    @abstractmethod
    async def execute(self, payload: MessagePayload) -> Any:
        """Executor main method.

        Responsible with executing the payload and adding implementing
        additional layers of error handling and retries:

        - Should decide whether to propagate errors to the queue layer.
        - Should decide whether retries are applicable.

        Args:
            payload: A standard message payload.

        Returns:
            Per executor/task specific. Might be None, metadata, identifiers, etc.
        """


class ConsumerBase(ABC):
    """Async core pipeline shared by polling and push transports.

    The transport decides *how* raw messages arrive. The base class provides:
      - decode/preprocess
      - execute with retries
      - ack with retries (+ critical event on exhaustion)
      - invalid/failing handlers
    """

    def __init__(
        self, config: ConsumerRuntimeConfig, executor: Executor
    ) -> None:
        """Consumer base constructor.

        Args:
            config: The consumer config object.
            executor: An executor instance.
        """
        self._cfg = config
        self._executor = executor

    @property
    def config(self) -> ConsumerRuntimeConfig:
        """Implements the 'config' property.

        Returns:
            The consumer config object.
        """
        return self._cfg

    # -------- backend hooks (required) --------

    @abstractmethod
    async def preprocess_message(self, raw_message: Any) -> MessageEnvelope:
        """Decode/Validate broker message and wrap to MessageEnvelope.

        Args:
            raw_message: Broker-specific message.

        Returns:
            A MessageEnvelope object.
        """
        raise NotImplementedError

    async def process_message(self, message: MessageEnvelope) -> None:
        """Execution of message payload.

        Args:
            message: A MessageEnvelope object.
        """
        if self.config.blocking_execution:
            await self._executor.execute(payload=message.payload)
        else:
            asyncio.create_task(
                self._executor.execute(payload=message.payload)
            )

    @abstractmethod
    async def acknowledge_message(
        self, message_id: str, raw_message: Any
    ) -> None:
        """Acks/Deletes message from the queue.

        Args:
            message_id: The ID of the message.
            raw_message: The raw broker-specific message.
        """
        raise NotImplementedError

    @abstractmethod
    async def handle_invalid_message(self, raw_message: Any) -> None:
        """Handles message of invalid format (not suitable for execution).

        Messages that are invalid should still be acked to avoid
        looping execution and system poisoning.

        Args:
            raw_message: The raw broker-specific message.

        """
        raise NotImplementedError

    async def handle_critical_event(self, event: CriticalEvent) -> None:
        """Critical event handler.

        A critical event indicates that the application behavior has degraded.
        For instance, the inability to serialize the message to a broker-compatible format
        is extremely severe as it most probably repeats across messages meaning no messages
        are published for execution at all.

        A complete implementation of a critical event handling process would be the following:

        1. Log in detailed fashion the event so that it is traceable in the logs.
        2. Publish the event to an event aggregator service so that it is tracked long-term and
        alerts can be generated based on its frequency and severity.
        3. Hold the message in a DLQ to enable re-execution when a bug fix is introduced in the code.

        Args:
            event: A critical event instance.
        """
        # TODO: Extend with more tooling/operations.
        logger.error("Critical event handler received event: %s", event)

    async def handle_raw_message(self, raw_message: Any) -> None:
        """Handles one message at a time.

        Args:
            raw_message: A raw broker-specific message.
        """
        try:
            msg = await self.preprocess_message(raw_message)
        except MessageDecodeError:
            await self.handle_invalid_message(raw_message)
            return

        if self.config.late_ack:
            await self._process_with_retries(msg)
            await self._ack_with_retries(msg)
        else:
            await self._ack_with_retries(msg)
            await self._process_with_retries(msg)

    async def _process_with_retries(self, message: MessageEnvelope) -> None:
        attempts = self.config.execution_retries + 1

        for attempt in range(attempts):
            try:
                await self.process_message(message)
                return
            except Exception as exc:
                logger.error(
                    "Failed to process message %s: %s (attempt=%s)",
                    message.payload.id,
                    exc,
                    attempt,
                )

        await self.handle_critical_event(
            CriticalEvent(
                value=CriticalEventType.execute_failed,
                description=f"Execution failed for message {message.id}",
                created_at=datetime.now(tz=timezone.utc),
            )
        )

    async def _ack_with_retries(self, message: MessageEnvelope) -> None:
        attempts = self.config.ack_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                await self.acknowledge_message(
                    message_id=message.id, raw_message=message.raw_message
                )
                return
            except Exception as exc:
                logger.error(
                    "Failed to ack message %s: %s (attempt=%s)",
                    message.payload.id,
                    exc,
                    attempt,
                )
                await asyncio.sleep(self.config.ack_retry_backoff)

        await self.handle_critical_event(
            CriticalEvent(
                value=CriticalEventType.ack_failed,
                description=f"Ack failed for message {message.id}",
                created_at=datetime.now(tz=timezone.utc),
            )
        )


class PollingConfig(ConsumerRuntimeConfig):
    """Base config class for polling consumers."""

    interval: float = Field(
        default=1.0, description="Polling interval in seconds."
    )
    jitter: float = Field(
        default=0.0,
        description="Jitter(+- random diff) for interval in seconds.",
    )


class PollingConsumer(ConsumerBase, ABC):
    """Polling transport: the consumer fetches batches periodically."""

    def __init__(self, config: PollingConfig, executor: Executor) -> None:
        """Polling consumer constructor.

        Args:
            config: Polling config instance.
            executor: Executor instance.
        """
        super().__init__(config, executor=executor)
        self._stopped = asyncio.Event()

        self._task: asyncio.Task[None] | None = None

        # Jitter is computed once at construction (fixed for this consumer instance).
        self._polling_interval = config.interval + random.uniform(
            -config.jitter, config.jitter
        )

    def start(self) -> None:
        """Run in the background on the current running event loop."""
        if self._task is not None and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self.run())

    def stop(self) -> None:
        """Signal the run loop to stop."""
        self._stopped.set()

    @property
    def polling_interval(self) -> float:
        """Implement the 'polling_interval' property.

        Returns:
            The polling interval value.
        """
        return self._polling_interval

    @abstractmethod
    async def receive_messages(self) -> list[Any]:
        """Requests to get a batch of messages from the queue.

        Returns:
            A list of messages (broker-specific payload).
        """
        raise NotImplementedError

    async def poll_once(self) -> None:
        """Receive and handle one batch. Receive failures emit read_failed."""
        try:
            raw_messages = await self.receive_messages()
        except Exception as exc:
            await self.handle_critical_event(
                CriticalEvent(
                    value=CriticalEventType.read_failed,
                    description=f"Receive failed: {exc!r}",
                    created_at=datetime.now(tz=timezone.utc),
                )
            )
            return

        for raw in raw_messages:
            await self.handle_raw_message(raw)

    async def run(self) -> None:
        """Run polling loop until stop() is called."""
        while not self._stopped.is_set():
            start = asyncio.get_running_loop().time()
            await self.poll_once()

            elapsed = asyncio.get_running_loop().time() - start
            remaining = self.polling_interval - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
