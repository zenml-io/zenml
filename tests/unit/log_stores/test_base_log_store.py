#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from zenml.log_stores.base_log_store import BaseLogStore, BaseLogStoreOrigin
from zenml.models import LogsResponse
from zenml.utils.logging_utils import LogEntry


class DummyLogStore(BaseLogStore):
    """Dummy log store for testing."""

    def emit(
        self,
        origin: BaseLogStoreOrigin,
        record: logging.LogRecord,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass

    def _release_origin(self, origin: BaseLogStoreOrigin) -> None:
        pass

    def flush(self, blocking: bool = True) -> None:
        pass

    def fetch(
        self,
        logs_model: LogsResponse,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[LogEntry]:
        return []


class TestBaseLogStore:
    """Tests for the BaseLogStore class."""

    def test_log_filter_hook(self):
        """Test that the log filter hook can be set and retrieved."""
        # Bypass full Pydantic instantiation for a fast unit test
        store = BaseLogStore.__new__(DummyLogStore)
        store._log_filter = None

        assert store.log_filter is None

        def dummy_filter(
            record: logging.LogRecord,
        ) -> Optional[logging.LogRecord]:
            return record

        store.set_log_filter(dummy_filter)
        assert store.log_filter == dummy_filter
