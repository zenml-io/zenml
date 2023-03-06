#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import atexit
import logging
import numbers

from six import string_types

from zenml.analytics.consumer import Consumer
from zenml.analytics.request import post

try:
    import queue
except ImportError:
    import Queue as queue

ID_TYPES = (numbers.Number, string_types)

logger = logging.getLogger(__name__)


class Client(object):
    class DefaultConfig(object):
        on_error = None
        debug = False
        send = True
        sync_mode = False
        max_queue_size = 10000
        timeout = 15
        max_retries = 1
        thread = 1
        upload_interval = 0.5
        upload_size = 100

    def __init__(
        self,
        debug=DefaultConfig.debug,
        max_queue_size=DefaultConfig.max_queue_size,
        send=DefaultConfig.send,
        on_error=DefaultConfig.on_error,
        max_retries=DefaultConfig.max_retries,
        sync_mode=DefaultConfig.sync_mode,
        timeout=DefaultConfig.timeout,
        thread=DefaultConfig.thread,
        upload_size=DefaultConfig.upload_size,
        upload_interval=DefaultConfig.upload_interval,
    ):

        self.queue = queue.Queue(max_queue_size)
        self.on_error = on_error
        self.debug = debug
        self.send = send
        self.sync_mode = sync_mode
        self.timeout = timeout

        if debug:
            logger.setLevel(logging.DEBUG)

        if sync_mode:
            self.consumers = None
        else:
            # On program exit, allow the consumer thread to exit cleanly.
            # This prevents exceptions and a messy shutdown when the
            # interpreter is destroyed before the daemon thread finishes
            # execution. However, it is *not* the same as flushing the queue!
            # To guarantee all messages have been delivered, you'll still need
            # to call flush().
            if send:
                atexit.register(self.join)
            for _ in range(thread):
                self.consumers = []
                consumer = Consumer(
                    self.queue,
                    on_error=on_error,
                    upload_size=upload_size,
                    upload_interval=upload_interval,
                    retries=max_retries,
                    timeout=timeout,
                )
                self.consumers.append(consumer)

                # if we've disabled sending, just don't start the consumer
                if send:
                    consumer.start()

    def identify(self, user_id, traits):
        return self._enqueue(
            msg={
                "user_id": str(user_id),
                "traits": traits,
                "type": "identify",
            }
        )

    def track(self, user_id, event, properties):
        return self._enqueue(
            msg={
                "user_id": str(user_id),
                "event": event,
                "properties": properties,
                "type": "track",
            }
        )

    def group(self, user_id, group_id, traits):
        return self._enqueue(
            msg={
                "user_id": str(user_id),
                "group_id": str(group_id),
                "traits": traits,
                "type": "group",
            }
        )

    def _enqueue(self, msg):
        """Push a new `msg` onto the queue, return `(success, msg)`"""
        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        if self.sync_mode:
            post(timeout=self.timeout, batch=[msg])
            return True, msg

        try:
            self.queue.put(msg, block=False)
            return True, msg
        except queue.Full:
            logger.warning("ZenML analytics-python queue is full")
            return False, msg

    def flush(self):
        """Forces a flush from the internal queue to the server"""
        queue = self.queue
        size = queue.qsize()
        queue.join()
        # Note that this message may not be precise, because of threading.
        logger.debug("successfully flushed about %s items.", size)

    def join(self):
        """Ends the consumer thread once the queue is empty.
        Blocks execution until finished
        """
        for consumer in self.consumers:
            consumer.pause()
            try:
                consumer.join()
            except RuntimeError:
                # consumer thread has not started
                pass

    def shutdown(self):
        """Flush all messages and cleanly shutdown the client"""
        self.flush()
        self.join()
