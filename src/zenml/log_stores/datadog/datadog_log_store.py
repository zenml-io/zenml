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
"""Datadog log store implementation."""

import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast

import requests
from pydantic import BaseModel, ConfigDict

from zenml.enums import LoggingLevels
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.datadog.datadog_log_exporter import DatadogLogExporter
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.models.v2.misc.log_models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
)

logger = get_logger(__name__)


class DatadogLogStoreOlderCursorPos(BaseModel):
    """Datadog cursor position for paging older logs."""

    dd_after: str

    model_config = ConfigDict(extra="forbid")


class DatadogLogStoreNewerCursorPos(BaseModel):
    """Datadog cursor position for paging newer logs."""

    ts: Optional[str] = None
    dd_id: str = ""

    model_config = ConfigDict(extra="forbid")


DatadogLogStoreCursorPos = Union[
    DatadogLogStoreOlderCursorPos, DatadogLogStoreNewerCursorPos
]


class DatadogLogStoreCursor(BaseModel):
    """Cursor payload for Datadog pagination tokens."""

    v: int = 1
    backend: Literal["datadog"] = "datadog"
    logs_id: str
    pos: DatadogLogStoreCursorPos

    model_config = ConfigDict(extra="forbid")


class DatadogLogStore(OtelLogStore):
    """Log store that exports logs to Datadog.

    This implementation extends OtelLogStore and configures it to send logs
    to Datadog's HTTP intake API.
    """

    _datadog_exporter: Optional[DatadogLogExporter] = None

    @property
    def config(self) -> DatadogLogStoreConfig:
        """Returns the configuration of the Datadog log store.

        Returns:
            The configuration.
        """
        return cast(DatadogLogStoreConfig, self._config)

    def get_exporter(self) -> DatadogLogExporter:
        """Get the Datadog log exporter.

        Returns:
            DatadogExporter with the proper configuration.
        """
        if not self._datadog_exporter:
            headers = {
                "dd-api-key": self.config.api_key.get_secret_value(),
                "dd-application-key": self.config.application_key.get_secret_value(),
            }
            if self.config.headers:
                headers.update(self.config.headers)

            self._datadog_exporter = DatadogLogExporter(
                endpoint=self.config.endpoint,
                headers=headers,
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._datadog_exporter

    def fetch(
        self,
        logs_model: "LogsResponse",
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List["LogEntry"]:
        """Fetch logs from Datadog's API.

        This method queries Datadog's Logs API to retrieve logs for the
        specified pipeline run and step. It automatically paginates through
        results to fetch up to the requested limit.

        Args:
            logs_model: The logs model containing run and step metadata.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from Datadog.
        """
        query_parts = [
            f"service:{self.config.service_name}",
            f"@zenml.log.id:{logs_model.id}",
        ]

        query = " ".join(query_parts)

        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )
        headers = {
            "DD-API-KEY": self.config.api_key.get_secret_value(),
            "DD-APPLICATION-KEY": self.config.application_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        log_entries: List[LogEntry] = []
        cursor: Optional[str] = None
        remaining = limit

        try:
            while remaining > 0:
                # Datadog API limit is 1000 per request
                page_limit = min(remaining, 1000)

                body: Dict[str, Any] = {
                    "filter": {
                        "query": query,
                        "from": (
                            start_time.isoformat()
                            if start_time
                            else logs_model.created.isoformat()
                        ),
                        "to": (
                            end_time.isoformat()
                            if end_time
                            else datetime.now().astimezone().isoformat()
                        ),
                    },
                    "page": {
                        "limit": page_limit,
                    },
                    "sort": "timestamp",
                }

                if cursor:
                    body["page"]["cursor"] = cursor

                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=body,
                    timeout=30,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch logs from Datadog: "
                        f"{response.status_code} - {response.text[:200]}"
                    )
                    break

                data = response.json()
                logs = data.get("data", [])

                if not logs:
                    break

                for log in logs:
                    entry = self._parse_log_entry(log)
                    if entry:
                        log_entries.append(entry)

                remaining -= len(logs)

                # Get cursor for next page
                cursor = data.get("meta", {}).get("page", {}).get("after")
                if not cursor:
                    break

            logger.debug(f"Fetched {len(log_entries)} logs from Datadog")
            return log_entries

        except Exception as e:
            logger.exception(f"Error fetching logs from Datadog: {e}")
            return log_entries  # Return what we have so far

    def fetch_entries(
        self,
        *,
        logs_model: LogsResponse,
        limit: int,
        before: Optional[str],
        after: Optional[str],
        filter_: LogsEntriesFilter,
    ) -> LogsEntriesResponse:
        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        if after is not None:
            watermark = self._decode_cursor(
                token=after,
                logs_id=str(logs_model.id),
            )
            items, _, after_pos = self._fetch_newer_page(
                logs_model=logs_model,
                limit=limit,
                filter_=filter_,
                watermark=watermark,
            )
            after_token = self._encode_cursor(
                logs_id=str(logs_model.id),
                pos=after_pos,
            )
            return LogsEntriesResponse(
                items=items, before=None, after=after_token
            )

        cursor_pos = None
        if before is not None:
            cursor_pos = self._decode_cursor(
                token=before,
                logs_id=str(logs_model.id),
            )

        items, before_pos, after_pos = self._fetch_latest_or_older_page(
            logs_model=logs_model,
            limit=limit,
            filter_=filter_,
            cursor_pos=cursor_pos,
        )
        before_token = (
            self._encode_cursor(
                logs_id=str(logs_model.id),
                pos=before_pos,
            )
            if before_pos is not None
            else None
        )
        after_token = (
            self._encode_cursor(
                logs_id=str(logs_model.id),
                pos=after_pos,
            )
            if after_pos is not None
            else None
        )
        return LogsEntriesResponse(
            items=items, before=before_token, after=after_token
        )

    def _encode_cursor(self, *, logs_id: str, pos: Dict[str, Any]) -> str:
        cursor = DatadogLogStoreCursor(logs_id=logs_id, pos=pos)
        data = json.dumps(
            cursor.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    def _decode_cursor(self, *, token: str, logs_id: str) -> Dict[str, Any]:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
        cursor = DatadogLogStoreCursor.model_validate(decoded)
        if cursor.logs_id != logs_id:
            raise ValueError("Cursor logs ID does not match.")
        return cast(Dict[str, Any], cursor.pos.model_dump())

    def _build_query(
        self, logs_model: LogsResponse, filter_: LogsEntriesFilter
    ) -> str:
        query_parts = [
            f"service:{self.config.service_name}",
            f"@zenml.log.id:{logs_model.id}",
        ]

        if filter_.level:
            name = filter_.level.name.lower()
            if name == "warning":
                name = "warn"
            query_parts.append(f"status:{name}")

        if filter_.search:
            # Best-effort translation; we still post-filter to match substring semantics.
            query_parts.append(filter_.search)

        return " ".join(query_parts)

    def _fetch_latest_or_older_page(
        self,
        *,
        logs_model: LogsResponse,
        limit: int,
        filter_: LogsEntriesFilter,
        cursor_pos: Optional[Dict[str, Any]],
    ) -> Tuple[
        List[LogEntry], Optional[Dict[str, Any]], Optional[Dict[str, Any]]
    ]:
        query = self._build_query(logs_model, filter_)
        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )
        headers = {
            "DD-API-KEY": self.config.api_key.get_secret_value(),
            "DD-APPLICATION-KEY": self.config.application_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        from_time = (
            filter_.since.isoformat()
            if filter_.since
            else logs_model.created.isoformat()
        )
        to_time = (
            filter_.until.isoformat()
            if filter_.until
            else datetime.now().astimezone().isoformat()
        )

        body: Dict[str, Any] = {
            "filter": {
                "query": query,
                "from": from_time,
                "to": to_time,
            },
            "page": {"limit": min(limit, 1000)},
            "sort": "-timestamp",
        }
        if cursor_pos and cursor_pos.get("dd_after"):
            body["page"]["cursor"] = cursor_pos["dd_after"]

        response = requests.post(
            api_endpoint,
            headers=headers,
            json=body,
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Datadog: {response.status_code}"
            )

        data = response.json()
        raw_logs = data.get("data", [])
        before_dd_after = data.get("meta", {}).get("page", {}).get("after")

        entries_with_ids: List[Tuple[str, LogEntry]] = []
        for raw in raw_logs:
            entry = self._parse_log_entry(raw)
            if entry is None:
                continue
            dd_id = raw.get("id", "")
            if not self._matches_filter(entry, filter_):
                continue
            entries_with_ids.append((dd_id, entry))

        items = [entry for _, entry in entries_with_ids]
        if not items:
            return ([], None, None)

        newest_dd_id = entries_with_ids[0][0]
        newest_ts = items[0].timestamp
        before_pos = {"dd_after": before_dd_after} if before_dd_after else None
        after_pos: Dict[str, Any] = {
            "ts": newest_ts.isoformat() if newest_ts else None,
            "dd_id": newest_dd_id,
        }
        return (items, before_pos, after_pos)

    def _fetch_newer_page(
        self,
        *,
        logs_model: LogsResponse,
        limit: int,
        filter_: LogsEntriesFilter,
        watermark: Dict[str, Any],
    ) -> Tuple[
        List[LogEntry], Optional[Dict[str, Any]], Optional[Dict[str, Any]]
    ]:
        query = self._build_query(logs_model, filter_)
        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )
        headers = {
            "DD-API-KEY": self.config.api_key.get_secret_value(),
            "DD-APPLICATION-KEY": self.config.application_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        watermark_ts_raw = watermark.get("ts")
        watermark_dd_id = str(watermark.get("dd_id") or "")
        if watermark_ts_raw:
            watermark_ts = datetime.fromisoformat(
                watermark_ts_raw.replace("Z", "+00:00")
            )
        else:
            watermark_ts = logs_model.created

        from_time = watermark_ts.isoformat()
        to_time = (
            filter_.until.isoformat()
            if filter_.until
            else datetime.now().astimezone().isoformat()
        )

        body: Dict[str, Any] = {
            "filter": {
                "query": query,
                "from": from_time,
                "to": to_time,
            },
            "page": {"limit": min(limit, 1000)},
            "sort": "timestamp",
        }

        response = requests.post(
            api_endpoint,
            headers=headers,
            json=body,
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Datadog: {response.status_code}"
            )

        data = response.json()
        raw_logs = data.get("data", [])

        entries_with_ids: List[Tuple[str, LogEntry]] = []
        for raw in raw_logs:
            entry = self._parse_log_entry(raw)
            if entry is None:
                continue
            dd_id = str(raw.get("id", ""))
            if not self._matches_filter(entry, filter_):
                continue

            # Drop entries at/before watermark (best-effort tie-breaker).
            if entry.timestamp is not None and entry.timestamp < watermark_ts:
                continue
            if (
                entry.timestamp is not None
                and entry.timestamp == watermark_ts
                and watermark_dd_id
                and dd_id <= watermark_dd_id
            ):
                continue

            entries_with_ids.append((dd_id, entry))

        if not entries_with_ids:
            return ([], None, watermark)

        # We fetched ascending; return newest->oldest.
        entries_with_ids.reverse()
        items = [entry for _, entry in entries_with_ids]

        newest_dd_id = entries_with_ids[0][0]
        newest_ts = items[0].timestamp
        after_pos: Dict[str, Any] = {
            "ts": newest_ts.isoformat() if newest_ts else None,
            "dd_id": newest_dd_id,
        }
        return (items, None, after_pos)

    def _matches_filter(
        self, entry: LogEntry, filter_: LogsEntriesFilter
    ) -> bool:
        if filter_.level is not None:
            if entry.level is None or entry.level != filter_.level:
                return False
        if filter_.since is not None:
            if entry.timestamp is None or entry.timestamp < filter_.since:
                return False
        if filter_.until is not None:
            if entry.timestamp is None or entry.timestamp > filter_.until:
                return False
        if filter_.search is not None:
            needle = filter_.search.lower().strip()
            if needle and needle not in entry.message.lower():
                return False
        return True

    def _parse_log_entry(self, log: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single log entry from Datadog's API response.

        Args:
            log: The log data from Datadog's API.

        Returns:
            A LogEntry object, or None if parsing fails.
        """
        try:
            log_fields = log.get("attributes", {})
            message = log_fields.get("message", "")
            nested_attrs = log_fields.get("attributes", {})

            if exc_info := nested_attrs.get("exception"):
                exc_message = exc_info.get("message")
                exc_type = exc_info.get("type")
                exc_stacktrace = exc_info.get("stacktrace")
                message += f"\n{exc_type}: {exc_message}\n{exc_stacktrace}"

            code_info = nested_attrs.get("code", {})
            filename = code_info.get("file", {}).get("path")
            lineno = code_info.get("line", {}).get("number")
            function_name = code_info.get("function", {}).get("name")

            otel_info = nested_attrs.get("otel", {})
            logger_name = otel_info.get("library", {}).get("name")

            timestamp = datetime.fromisoformat(
                log_fields["timestamp"].replace("Z", "+00:00")
            )

            severity = log_fields.get("status", "info").upper()
            log_severity = (
                LoggingLevels[severity]
                if severity in LoggingLevels.__members__
                else LoggingLevels.INFO
            )

            module = None
            if function_name:
                module = function_name
            elif filename:
                module = filename.rsplit("/", 1)[-1].replace(".py", "")

            return LogEntry(
                message=message,
                level=log_severity,
                timestamp=timestamp,
                name=logger_name,
                filename=filename,
                lineno=lineno,
                module=module,
            )
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup the Datadog log store.

        This method is called when the log store is no longer needed.
        """
        if self._datadog_exporter:
            self._datadog_exporter.shutdown()
            self._datadog_exporter = None
