import colorsys
import logging
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeAlias, Union
from uuid import uuid4

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

PlotDataPoint: TypeAlias = Optional[
    Tuple[Union[datetime, int, float], Union[int, float], str]
]
PlotFunction: TypeAlias = Callable[["LogLine", Any], PlotDataPoint]


class LogType(Enum):
    """Log types."""

    # API stages
    API = "api"
    API_RECEIVED = "api_received"
    API_QUEUED = "api_queued"
    API_THROTTLED = "api_throttled"
    API_ACCEPTED = "api_accepted"
    API_COMPLETED = "api_completed"
    CLIENT_RETRY = "client_retry"

    # Endpoint stages
    ENDPOINT = "endpoint"
    ENDPOINT_ASYNC_STARTED = "endpoint_async_started"
    ENDPOINT_ASYNC_COMPLETED = "endpoint_async_completed"
    ENDPOINT_SYNC_STARTED = "endpoint_sync_started"
    ENDPOINT_SYNC_COMPLETED = "endpoint_sync_completed"

    # Database stages
    SQL = "sql"
    SQL_STARTED = "sql_started"
    SQL_COMPLETED = "sql_completed"

    # RBAC stages
    RBAC = "rbac"
    RBAC_STARTED = "rbac_started"
    RBAC_COMPLETED = "rbac_completed"


class LogLine(BaseModel):
    """Represents a parsed log line with all possible fields."""

    log_type: LogType
    timestamp: datetime
    pod: Optional[str] = None
    request_id: str  # Either HTTP request ID or thread name
    client_type: Optional[str] = None  # Python, Web UI, etc.
    transaction_id: Optional[str] = None  # Transaction ID for retries
    api_method: Optional[str] = None  # HTTP method for API calls
    api_path: Optional[str] = None
    ip_address: Optional[str] = None
    status_code: Optional[int] = None
    target: Optional[str] = None  # The code target being executed
    metrics: Dict[str, Any] = Field(default_factory=dict)


class LogFile(BaseModel):
    """Container for parsed log lines with helper methods."""

    lines: List[LogLine] = Field(default_factory=list)
    # Track request flows
    request_flows: Dict[str, List[LogLine]] = Field(default_factory=dict)

    def add_line(self, line: LogLine) -> None:
        """Add a log line and update request flows."""
        self.lines.append(line)
        if line.request_id:
            if (
                not line.transaction_id
                and line.api_path == "/api/v1/users"
                and line.api_method == "GET"
            ):
                return
            previous_line = None
            if line.request_id not in self.request_flows:
                self.request_flows[line.request_id] = []
                if not line.transaction_id:
                    line.transaction_id = str(uuid4())[:4]
            else:
                previous_line = self.request_flows[line.request_id][-1]

                # Auto-detect transactions and retries if the transaction IDs are missing
                if not line.transaction_id:
                    if (
                        line.log_type == LogType.API_RECEIVED
                        or previous_line.log_type == LogType.API_COMPLETED
                    ):
                        # New transaction / retry detected
                        line.transaction_id = str(uuid4())[:4]
                    else:
                        # No new transaction / retry detected, use the previous one
                        line.transaction_id = previous_line.transaction_id

            self.request_flows[line.request_id].append(line)

    @staticmethod
    def _parse_metrics(metrics_str: str) -> Dict[str, Any]:
        """Parse metrics from the log line metrics section.

        Args:
            metrics_str: String containing metrics in "key: value" format separated by spaces

        Returns:
            Dictionary containing parsed metrics
        """
        if not metrics_str:
            return {}

        metrics_dict = {}

        # Match key-value pairs where value can contain spaces until the next key or end
        # This will look ahead to find either another key:value pair or the end of string
        pattern = r"([^:]+):\s*([^:]*)(?=\s+[^:]+:|$)"

        # Find all matches in the metrics string
        matches = re.finditer(pattern, metrics_str)

        for match in matches:
            key = match.group(1).strip()
            value = match.group(2).strip()

            # Skip empty values
            if not value:
                continue

            # Try to convert numeric values
            try:
                # Try integer first
                if value.isdigit():
                    metrics_dict[key] = int(value)
                # Then try float
                else:
                    metrics_dict[key] = float(value)
            except ValueError:
                # If not numeric, keep as string
                metrics_dict[key] = value

        # # Extract threads
        # if match := re.search(r"threads:\s*(\d+)", metrics_str):
        #     metrics_dict["threads"] = int(match.group(1))

        # # Extract active requests
        # if match := re.search(r"active_requests:\s*(\d+)", metrics_str):
        #     metrics_dict["active_requests"] = int(match.group(1))

        # # Extract file descriptors
        # if match := re.search(
        #     r"file_descriptors:\s*(\d+)\s*/\s*(\d+)", metrics_str
        # ):
        #     metrics_dict["file_descriptor_count"] = int(match.group(1))
        #     metrics_dict["file_descriptor_limit"] = int(match.group(2))

        # # Extract memory
        # if match := re.search(r"memory:\s*([\d.]+)MB", metrics_str):
        #     metrics_dict["memory_usage"] = float(match.group(1))

        # # Extract thread info
        # if match := re.search(
        #     r"current_thread:\s*([^(]+)\s*\(([^)]+)\)", metrics_str
        # ):
        #     metrics_dict["current_thread_name"] = match.group(1).strip()
        #     metrics_dict["current_thread_id"] = match.group(2).strip()

        # # Extract connection info
        # if "conn(active)" in metrics_str:
        #     active = re.search(r"conn\(active\):\s*(\d+)", metrics_str)
        #     idle = re.search(r"conn\(idle\):\s*(\d+)", metrics_str)
        #     overflow = re.search(r"conn\(overflow\):\s*(\d+)", metrics_str)

        #     if active:
        #         metrics_dict["active_connections"] = int(active.group(1))
        #     if idle:
        #         metrics_dict["idle_connections"] = int(idle.group(1))
        #     if overflow:
        #         metrics_dict["overflow_connections"] = int(overflow.group(1))

        return metrics_dict

    @staticmethod
    def _parse_pod_and_timestamp(line: str) -> Tuple[Optional[str], datetime]:
        """Extract pod name and timestamp from the log line."""
        pod_match = re.search(r"\[pod/([^/]+)/[^\]]+\]", line)
        pod = pod_match.group(1) if pod_match else None

        # Extract timestamp
        timestamp_match = re.search(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})", line
        )
        if not timestamp_match:
            raise ValueError(f"Could not parse timestamp from line: {line}")

        timestamp = datetime.strptime(
            timestamp_match.group(1), "%Y-%m-%d %H:%M:%S,%f"
        )
        return pod, timestamp

    @staticmethod
    def _parse_request_id(
        line: str,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Extract request ID from the log line."""
        request_id_match = re.search(
            r"DEBUG.*\[([^\]]+)\](\s+([A-Z]+)\s+STATS)", line
        )
        full_request_id = (
            request_id_match.group(1) if request_id_match else "unknown"
        )
        request_tokens = full_request_id.split("/")
        request_id = request_tokens[0]
        client_type = request_tokens[1] if len(request_tokens) > 1 else None
        transaction_id = request_tokens[2] if len(request_tokens) > 2 else None
        return request_id, client_type, transaction_id

    @staticmethod
    def _parse_api_stats(line: str) -> Tuple[LogType, dict, Optional[float]]:
        """Parse API STATS log lines."""
        data = {}
        duration = None

        # Extract HTTP method and path
        if method_path_match := re.search(
            r"(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)", line
        ):
            data["api_method"] = method_path_match.group(1)
            data["api_path"] = method_path_match.group(2)

        # Extract IP address
        if ip_match := re.search(r"from\s+(\d+\.\d+\.\d+\.\d+)", line):
            data["ip_address"] = ip_match.group(1)

        # Determine log type and extract duration
        if "RECEIVED" in line:
            log_type = LogType.API_RECEIVED
        elif "QUEUED" in line:
            log_type = LogType.API_QUEUED
        elif "THROTTLED" in line:
            log_type = LogType.API_THROTTLED
            if duration_match := re.search(r"after\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        elif "ACCEPTED" in line:
            log_type = LogType.API_ACCEPTED
            if duration_match := re.search(r"after\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        elif status_match := re.search(
            r"(\d{3})\s+(?:GET|POST|PUT|DELETE|PATCH)", line
        ):
            log_type = LogType.API_COMPLETED
            data["status_code"] = int(status_match.group(1))
            if duration_match := re.search(r"took\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        else:
            raise ValueError(f"Unknown API STATS type in line: {line}")

        return log_type, data, duration

    @staticmethod
    def _parse_endpoint_stats(
        line: str,
    ) -> Tuple[LogType, dict, Optional[float]]:
        """Parse ENDPOINT STATS log lines."""
        data = {}
        duration = None

        # Extract target operation
        if target_match := re.search(
            r"ENDPOINT STATS - (?:async|sync)\s+([^\s]+)", line
        ):
            data["target"] = target_match.group(1)

        # Determine log type and extract duration
        if "async" in line and "STARTED" in line:
            log_type = LogType.ENDPOINT_ASYNC_STARTED
        elif "async" in line and "took" in line:
            log_type = LogType.ENDPOINT_ASYNC_COMPLETED
            if duration_match := re.search(r"took\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        elif "sync" in line and "STARTED" in line:
            log_type = LogType.ENDPOINT_SYNC_STARTED
            if duration_match := re.search(r"after\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        elif "sync" in line and "took" in line:
            log_type = LogType.ENDPOINT_SYNC_COMPLETED
            if duration_match := re.search(r"took\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        else:
            raise ValueError(f"Unknown ENDPOINT STATS type in line: {line}")

        return log_type, data, duration

    @staticmethod
    def _parse_sql_stats(line: str) -> Tuple[LogType, dict, Optional[float]]:
        """Parse SQL STATS log lines."""
        data = {}
        duration = None

        # Extract target operation
        if target_match := re.search(r"SQL STATS.*'([^']+)'", line):
            data["target"] = target_match.group(1)

        # Determine log type and extract duration
        if "started" in line:
            log_type = LogType.SQL_STARTED
        elif "completed" in line:
            log_type = LogType.SQL_COMPLETED
            if duration_match := re.search(r"in\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        else:
            raise ValueError(f"Unknown SQL STATS type in line: {line}")

        return log_type, data, duration

    @staticmethod
    def _parse_rbac_stats(line: str) -> Tuple[LogType, dict, Optional[float]]:
        """Parse RBAC STATS log lines."""
        data = {}
        duration = None

        # Extract HTTP method and path
        if method_path_match := re.search(
            r"(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)", line
        ):
            data["api_method"] = method_path_match.group(1)
            data["api_path"] = method_path_match.group(2)

        # Determine log type and extract duration
        if "started" in line:
            log_type = LogType.RBAC_STARTED
        elif "completed" in line:
            log_type = LogType.RBAC_COMPLETED
            if status_match := re.search(
                r"(\d{3})\s+(?:GET|POST|PUT|DELETE|PATCH)", line
            ):
                data["status_code"] = int(status_match.group(1))
            if duration_match := re.search(r"in\s+([\d.]+)ms", line):
                duration = float(duration_match.group(1))
        else:
            raise ValueError(f"Unknown RBAC STATS type in line: {line}")

        return log_type, data, duration

    @staticmethod
    def _anonymize_api_path(api_path: str) -> str:
        """Anonymize the URL path of an API call."""
        # Replace all UUIDs with a placeholder
        return re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "<uuid>",
            api_path,
        )

    @classmethod
    def parse_logs(cls, filename: str) -> "LogFile":
        """Parse log lines from a file."""
        log_file = cls()
        log_lines = []

        with open(filename, "r") as f:
            for line in f:
                # Skip lines that don't contain STATS
                if "STATS" not in line:
                    continue

                try:
                    # Extract common fields
                    pod, timestamp = cls._parse_pod_and_timestamp(line)
                    request_id, client_type, transaction_id = (
                        cls._parse_request_id(line)
                    )

                    # Extract metrics if present
                    metrics_match = re.search(r"\[\s+(.*)\s+\]", line)
                    metrics = cls._parse_metrics(
                        metrics_match.group(1) if metrics_match else None
                    )

                    # Parse based on stats type
                    if "API STATS" in line:
                        log_type, data, duration = cls._parse_api_stats(line)
                    elif "ENDPOINT STATS" in line:
                        log_type, data, duration = cls._parse_endpoint_stats(
                            line
                        )
                    elif "SQL STATS" in line:
                        log_type, data, duration = cls._parse_sql_stats(line)
                    elif "RBAC STATS" in line:
                        log_type, data, duration = cls._parse_rbac_stats(line)
                    else:
                        continue

                    if duration is not None:
                        metrics["duration"] = duration

                    # Create and add log line
                    log_line = LogLine(
                        log_type=log_type,
                        timestamp=timestamp,
                        pod=pod,
                        request_id=request_id,
                        client_type=client_type,
                        transaction_id=transaction_id,
                        metrics=metrics,
                        **data,
                    )
                    log_lines.append(log_line)

                except Exception as e:
                    # Log error but continue processing
                    logging.error(
                        f"Error parsing line: {line.strip()}\nError: {str(e)}"
                    )
                    continue

            # Sort by start time
            log_lines.sort(key=lambda x: x.timestamp)

            for log_line in log_lines:
                log_file.add_line(log_line)

        return log_file

    @staticmethod
    def generate_distinct_colors(n: int) -> np.ndarray:
        """Generate n visually distinct colors using golden ratio method with randomization.

        This creates a better spread of colors than linear HSV distribution.
        The golden ratio approach helps ensure maximum separation between hues.
        Adding saturation and value variation increases visual distinction.
        """
        colors = []
        golden_ratio = 0.618033988749895  # Golden ratio conjugate
        hue = random.random()  # Random starting hue

        for i in range(n):
            hue = (hue + golden_ratio) % 1.0
            # Vary saturation between 0.7-1.0 for good color strength
            saturation = 0.7 + random.random() * 0.3
            # Vary value between 0.8-1.0 to keep colors bright but distinct
            value = 0.8 + random.random() * 0.2

            # Convert HSV to RGB
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            # Append as RGBA (alpha=1.0)
            colors.append((*rgb, 1.0))

        # Shuffle the colors to avoid any remaining sequential patterns
        random.shuffle(colors)
        return np.array(colors)

    def get_plot_fn(
        self,
        y_metric: str,
        log_type: Optional[Union[LogType, List[LogType]]] = None,
        x_metric: Optional[str] = None,
        label_metric: Optional[str] = None,
        label_attribute: Optional[str] = None,
        min_x: Optional[Union[datetime, int, float]] = None,
        max_x: Optional[Union[datetime, int, float]] = None,
        plot_outside_x: bool = False,
        min_y: Optional[Union[int, float]] = None,
        max_y: Optional[Union[int, float]] = None,
        plot_outside_y: bool = False,
    ) -> PlotFunction:
        """Get a function that can be used to plot the data from the log file.

        Args:
            y_metric: The name of the metric to plot on the y-axis.
            log_types: The types of log lines to plot.
            x_metric: The name of the metric to plot on the x-axis. If not
                provided, the timestamp will be used.
            label_metric: The name of the metric to use for the label. If not
                provided, the log_type will be used to decide a label.
            label_attribute: The attribute of the log line to use for the label.
                If not provided, the log_type will be used to decide a label.
            min_x: The minimum x-value to plot.
            max_x: The maximum x-value to plot.
            plot_outside_x: Whether to plot outside the min_x and max_x values.
            min_y: The minimum y-value to plot.
            max_y: The maximum y-value to plot.
            plot_outside_y: Whether to plot outside the min_y and max_y values.
        """
        if isinstance(log_type, LogType):
            log_type = [log_type]

        def plot_fn(line: LogLine, context: Any) -> PlotDataPoint:
            if log_type is not None and line.log_type not in log_type:
                return None

            x_value = None
            if x_metric and line.metrics:
                x_value = line.metrics.get(x_metric)
            else:
                x_value = line.timestamp

            y_value = None
            if line.metrics:
                y_value = line.metrics.get(y_metric)

            if x_value is None:
                logging.debug(
                    f"Skipping line: {line.log_type} {line.timestamp}: "
                    f"x_value is None"
                )
                return None

            if y_value is None:
                logging.debug(
                    f"Skipping line: {line.log_type} {line.timestamp}: "
                    f"y_value is None"
                )
                return None

            if not isinstance(x_value, (datetime, int, float)):
                logging.debug(
                    f"Skipping line: {line.log_type} {line.timestamp}: "
                    f"x_value is not a timestamp or number: {x_value}"
                )
                return None

            if not isinstance(y_value, (int, float)):
                logging.debug(
                    f"Skipping line: {line.log_type} {line.timestamp}: "
                    f"y_value is not a number: {y_value}"
                )
                return None

            label = None
            if label_metric is not None:
                label = line.metrics.get(label_metric)
            elif label_attribute is not None:
                label = getattr(line, label_attribute, None)
            elif line.log_type in [
                LogType.API,
                LogType.API_RECEIVED,
                LogType.API_QUEUED,
                LogType.API_ACCEPTED,
                LogType.API_COMPLETED,
            ]:
                label = f"{line.api_method} {self._anonymize_api_path(line.api_path)}"
            elif line.log_type in [
                LogType.ENDPOINT,
                LogType.ENDPOINT_ASYNC_STARTED,
                LogType.ENDPOINT_ASYNC_COMPLETED,
                LogType.ENDPOINT_SYNC_STARTED,
                LogType.ENDPOINT_SYNC_COMPLETED,
            ]:
                label = f"{line.target}"
            elif line.log_type in [
                LogType.SQL,
                LogType.SQL_STARTED,
                LogType.SQL_COMPLETED,
            ]:
                label = f"{line.target}"
            elif line.log_type in [
                LogType.RBAC,
                LogType.RBAC_STARTED,
                LogType.RBAC_COMPLETED,
            ]:
                label = f"{line.api_method} {line.api_path}"

            if label is None:
                label = "unlabeled"

            if min_x is not None and x_value < min_x:  # type: ignore
                if not plot_outside_x:
                    return None
                label = "excluded"
            if max_x is not None and x_value > max_x:  # type: ignore
                if not plot_outside_x:
                    return None
                label = "excluded"
            if min_y is not None and y_value < min_y:
                if not plot_outside_y:
                    return None
                label = "excluded"
            if max_y is not None and y_value > max_y:
                if not plot_outside_y:
                    return None
                label = "excluded"

            return (
                x_value,
                y_value,
                label,
            )

        return plot_fn

    def plot(
        self,
        get_plot_data: PlotFunction,
        plot_presence: bool = False,
        line_width: float = 0.6,
        context: Any = None,
        top_n: Optional[int] = None,
    ) -> None:
        """Plot the data from the log file.

        Args:
            get_plot_data: A function that takes a log line and a context and returns a tuple of x, y, and label.
            plot_presence: Whether to plot the presence of the operation.
            line_width: The width of the lines.
            context: Additional context to pass to the get_plot_data function.
            top_n: The number of top labels to plot.
        """
        x_values = []
        y_values = []
        labels = []
        min_x = None
        max_x = None
        min_y = None
        max_y = None

        for line in self.lines:
            plot_data = get_plot_data(line, context)
            if plot_data is None:
                # Log entry was skipped
                continue

            x_value, y_value, label = plot_data

            if plot_presence:
                x_value = 1

            if min_x is None or x_value < min_x:  # type: ignore
                min_x = x_value
            if max_x is None or x_value > max_x:  # type: ignore
                max_x = x_value
            if min_y is None or y_value < min_y:
                min_y = y_value
            if max_y is None or y_value > max_y:
                max_y = y_value

            labels.append(label)
            x_values.append(x_value)
            y_values.append(y_value)

        # Add start time to the plot
        x_values.append(min_x)
        y_values.append(max_y)
        labels.append("Start")

        # Add end time to the plot
        x_values.append(max_x)
        y_values.append(max_y)
        labels.append("End")

        if top_n is not None:
            # Sort labels by y_value
            labels_with_values = [
                (label, y_value) for label, y_value in zip(labels, y_values)
            ]
            labels_with_values.sort(key=lambda x: x[1], reverse=True)
            # Collect the top unique labels
            top_labels = []
            for label, _ in labels_with_values:
                if label not in top_labels:
                    top_labels.append(label)
                if len(top_labels) >= top_n:
                    break

            # Re-label the values that are not in the top_n
            labels = [
                label if label in top_labels else "other" for label in labels
            ]

        # Assign unique colors per label
        unique_labels = sorted(set(labels))
        num_labels = len(unique_labels)

        # Generate distinct colors for each unique label
        colors = self.generate_distinct_colors(num_labels)
        label_to_color = {
            label: colors[i] for i, label in enumerate(unique_labels)
        }
        bar_colors = [label_to_color[label] for label in labels]

        # Plot
        plt.figure(figsize=(30, 6))

        if isinstance(min_x, datetime) and isinstance(max_x, datetime):
            # Convert to seconds since start
            x_values = [(x - min_x).total_seconds() for x in x_values]

            # Create evenly spaced timestamps for markers
            num_ticks = 20  # Adjust this number to show more or fewer markers
            time_range = max_x - min_x
            time_delta = time_range.total_seconds()
            tick_times = [
                min_x + (time_range / (num_ticks - 1)) * i
                for i in range(num_ticks + 1)
            ]
            tick_values = [
                time_delta / num_ticks * i for i in range(num_ticks + 1)
            ]
            plt.xticks(
                tick_values,
                [t.strftime("%Y-%m-%d %H:%M:%S") for t in tick_times],
                rotation=45,
                ha="right",
            )

        plt.bar(x_values, y_values, color=bar_colors, width=line_width)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Title")

        plt.grid(True, axis="y")
        # plt.ylim(bottom=0)  # Ensures Y-axis starts at 0

        # Create legend
        handles = [
            plt.Line2D([0], [0], color=label_to_color[label], lw=6)
            for label in unique_labels
        ]
        plt.legend(handles, unique_labels)

        plt.tight_layout()
        plt.show()

    def sort_log_lines(self) -> None:
        """Sort log lines by timestamp."""
        self.lines.sort(key=lambda x: x.timestamp)
        for _, request_logs in self.request_flows.items():
            request_logs.sort(key=lambda x: x.timestamp)

    def plot_request_flows(
        self,
        start_time: Optional[Union[datetime, int, float]] = None,
        end_time: Optional[Union[datetime, int, float]] = None,
        max_requests: Optional[int] = None,
        api_call_filter: Optional[List[str]] = None,
        group_retry_requests: bool = True,
        pps: int = 30,
        ppr: int = 20,
        width: Optional[int] = None,
        height: Optional[int] = None,
        pod: Optional[Union[int, str]] = None,
        request_id: Optional[str] = None,
        hide_legend: bool = False,
        hide_y_axis: bool = False,
        min_duration: Optional[float] = None,
        min_total_duration: Optional[float] = None,
    ) -> None:
        """Plot request flows as a Gantt chart showing the progression of requests through stages.

        Args:
            start_time: The start time of the plot (seconds since start).
            end_time: The end time of the plot (seconds since start).
            max_requests: The maximum number of requests to plot.
            api_call_filter: The API calls to filter.
            group_retry_requests: Whether to group retry requests.
            pps: The number of pixels per second to plot.
            ppr: The number of requests per row.
            width: The width of the plot in pixels.
            height: The height of the plot in pixels.
            pod: The pod to plot. If an integer is provided, it will be used as
                the pod index.
            request_id: The request ID to plot.
            hide_legend: Whether to hide the legend.
            hide_y_axis: Whether to hide the y-axis.
            min_duration: The minimum duration of a request to plot.
            min_total_duration: The minimum total duration of a request to plot
                (includes queued time).
        """
        if isinstance(start_time, (int, float)):
            start_time = self.lines[0].timestamp + timedelta(
                seconds=start_time
            )
        if isinstance(end_time, (int, float)):
            end_time = self.lines[0].timestamp + timedelta(seconds=end_time)

        # Build a long-form DataFrame with (request_id, stage, start, end)
        rows = []
        metrics_columns = set()
        request_count = 0
        transaction_count = 0
        request_flows = self.request_flows
        if isinstance(pod, int):
            pods = [log.pod for log in self.lines]
            pod = pods[pod]

        if request_id is not None:
            request_flows = {request_id: request_flows[request_id]}
        for req_id, request_logs in request_flows.items():
            entry_point = request_logs[0]
            exit_point = request_logs[-1]
            start = entry_point.timestamp
            end = exit_point.timestamp
            if start_time and start < start_time:
                continue
            if end_time and end > end_time:
                continue
            if pod is not None and entry_point.pod != pod:
                continue

            # Find a request log that has an API call
            api_call_logs = [
                log
                for log in request_logs
                if log.log_type
                in [
                    LogType.API,
                    LogType.API_RECEIVED,
                    LogType.API_QUEUED,
                    LogType.API_THROTTLED,
                    LogType.API_ACCEPTED,
                    LogType.API_COMPLETED,
                ]
            ]
            if api_call_logs:
                api_call = (
                    f"{api_call_logs[0].api_method} "
                    f"{self._anonymize_api_path(api_call_logs[0].api_path)}"
                )
            else:
                # No API call found, skip this request
                continue

            if api_call_filter is not None and not any(
                re.match(pattern, api_call) for pattern in api_call_filter
            ):
                continue

            # Group entries by transaction ID
            grouped_transaction_logs = defaultdict(list)
            for log in request_logs:
                grouped_transaction_logs[log.transaction_id].append(log)

            # Figure out the attempt count for each transaction
            transaction_start_times = [
                (transaction_id, logs[0].timestamp)
                for transaction_id, logs in grouped_transaction_logs.items()
            ]
            transaction_start_times.sort(key=lambda x: x[1])
            request_attempt_count = {
                transaction_id: idx
                for idx, (transaction_id, _) in enumerate(
                    transaction_start_times
                )
            }

            for _, transaction_entries in grouped_transaction_logs.items():
                if len(transaction_entries) < 2:
                    continue
                transaction_count += 1
                start = transaction_entries[0].timestamp
                end = transaction_entries[-1].timestamp
                total_duration = (end - start).total_seconds()
                final_state = transaction_entries[-1].log_type.name
                if final_state == LogType.API_COMPLETED.name:
                    final_state = transaction_entries[-2].log_type.name

                def get_row(
                    prev_entry: LogLine,
                    next_entry: LogLine,
                    print_label: bool = False,
                    total_queued_duration: float = 0,
                ) -> Dict[str, Any]:
                    duration = (
                        next_entry.timestamp - prev_entry.timestamp
                    ).total_seconds()
                    prev_metrics = prev_entry.metrics
                    next_metrics = next_entry.metrics
                    pod = "N/A"
                    if prev_entry.pod and prev_entry.pod == next_entry.pod:
                        pod = prev_entry.pod
                    else:
                        pod = f"{prev_entry.pod} -> {next_entry.pod}"
                    label = ""
                    attempt_count = request_attempt_count[
                        next_entry.transaction_id
                    ]
                    if print_label:
                        attempt = ""
                        if len(request_attempt_count) > 1:
                            attempt = f" ATTEMPT {attempt_count + 1}/{len(request_attempt_count)}"
                        label = f"{total_duration - total_queued_duration:.3f}s (+{total_queued_duration:.3f}s queued) {api_call} (RID: {req_id} TID: {next_entry.transaction_id}){attempt}"

                    metrics = {
                        metric_name: f"{prev_metrics.get(metric_name)} -> {next_metrics.get(metric_name)}"
                        if prev_metrics.get(metric_name)
                        != next_metrics.get(metric_name)
                        else f"{prev_metrics.get(metric_name)}"
                        for metric_name in prev_metrics.keys()
                    }
                    metrics_columns.update(metrics.keys())
                    return {
                        **metrics,
                        "request": f"{api_call} ({req_id}/{next_entry.transaction_id})",
                        "api_call": api_call,
                        "request_id": req_id,
                        "transaction_id": next_entry.transaction_id,
                        "attempt": f"{attempt_count + 1}/{len(request_attempt_count)}",
                        "stage": f"{prev_entry.log_type.name} -> {next_entry.log_type.name}",
                        "start": pd.to_datetime(prev_entry.timestamp),
                        "end": pd.to_datetime(next_entry.timestamp),
                        "state": prev_entry.log_type.name,
                        "final_state": final_state,
                        "target": prev_entry.target or api_call,
                        "label": label,
                        "duration": f"{duration:.3f}s / {total_duration:.3f}s",
                        "pod": pod,
                    }

                transaction_rows = []
                if group_retry_requests:
                    transaction_entry_point = transaction_entries[0]
                    # Add a "client retry" row for every other transaction
                    if (
                        transaction_entry_point.transaction_id
                        != request_logs[0].transaction_id
                    ):
                        row = get_row(request_logs[0], transaction_entry_point)
                        row["stage"] = (
                            f"{LogType.CLIENT_RETRY.name} -> {LogType.API_RECEIVED.name}"
                        )
                        row["state"] = LogType.CLIENT_RETRY.name
                        transaction_rows.append(row)

                total_queued_duration = 0
                for i in range(len(transaction_entries) - 1):
                    log = transaction_entries[i]
                    next_entry = transaction_entries[i + 1]
                    if log.log_type == LogType.API_QUEUED:
                        total_queued_duration += (
                            next_entry.timestamp - log.timestamp
                        ).total_seconds()

                    # If the current stage takes zero or negative time, it won't
                    # be plotted correctly.
                    # In that case, we cheat and simply simulate a one millisecond
                    # delay.
                    if next_entry.timestamp <= log.timestamp:
                        next_entry.timestamp = log.timestamp + timedelta(
                            milliseconds=1
                        )

                    row = get_row(
                        log,
                        next_entry,
                        print_label=i == len(transaction_entries) - 2,
                        total_queued_duration=total_queued_duration,
                    )

                    transaction_rows.append(row)

                if (
                    min_duration is not None
                    and total_duration - total_queued_duration < min_duration
                ):
                    continue
                if (
                    min_total_duration is not None
                    and total_duration < min_total_duration
                ):
                    continue
                rows.extend(transaction_rows)

            request_count += 1
            if max_requests is not None and request_count >= max_requests:
                break

        df = pd.DataFrame(rows)

        print(f"Plotting {len(rows)} entries for {request_count} requests")

        # Define a fixed color scheme for states
        color_map = {
            "API_RECEIVED": "#1f77b4",  # blue
            "API_QUEUED": "#FF1E1E",  # bright red
            "API_THROTTLED": "#d62728",  # darker red
            "API_ACCEPTED": "#2ca02c",  # green
            "API_COMPLETED": "#9467bd",  # purple
            "CLIENT_RETRY": "#FFD700",  # bright gold
            "ENDPOINT_ASYNC_STARTED": "#e377c2",  # pink
            "ENDPOINT_ASYNC_COMPLETED": "#7f7f7f",  # gray
            "ENDPOINT_SYNC_STARTED": "#bcbd22",  # olive
            "ENDPOINT_SYNC_COMPLETED": "#17becf",  # cyan
            "SQL_STARTED": "#00FF00",  # bright green
            "SQL_COMPLETED": "#ffbb78",  # light orange
            "RBAC_STARTED": "#98df8a",  # light green
            "RBAC_COMPLETED": "#ff9896",  # light red
        }

        # Plot as a Gantt chart using timeline
        plot_height = height or transaction_count * ppr + 200
        time_range = (df["end"].max() - df["start"].min()).total_seconds()
        plot_width = width or int(time_range * pps) + 300

        fig = px.timeline(
            df,
            x_start="start",
            x_end="end",
            y="request",
            color="state",
            text="label",
            title="API Request Flow Timeline",
            height=plot_height,
            width=plot_width,
            color_discrete_map=color_map,  # Use our fixed color mapping
            hover_data={
                **{metric: True for metric in metrics_columns},
                "request": True,
                "attempt": True,
                "start": True,
                "end": True,
                "target": True,
                "duration": True,
                "pod": True,
                "stage": True,
                "final_state": True,
            },
        )

        fig.update_layout(
            dragmode="pan",
        )

        if hide_legend:
            fig.update_layout(showlegend=False)
        if hide_y_axis:
            fig.update_layout(
                yaxis=dict(showticklabels=False, title=None), title=None
            )

        fig.update_yaxes(autorange="reversed")  # requests from top to bottom

        # Configure the modebar position
        fig.show(
            config=dict(
                scrollZoom=True,
                displayModeBar=True,
                displaylogo=False,
                fillFrame=True,
                modeBarButtonsToRemove=["zoomIn", "zoomOut"],
            )
        )
