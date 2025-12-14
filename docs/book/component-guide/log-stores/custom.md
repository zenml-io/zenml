---
description: Learning how to develop a custom log store.
---

# Develop a Custom Log Store

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

ZenML comes equipped with [Log Store implementations](./#log-store-flavors) that you can use to store logs in your artifact store, export to OpenTelemetry-compatible backends, or send to Datadog. However, if you need to use a different logging backend, you can extend ZenML to provide your own custom Log Store implementation.

### Base Abstraction

The log store is responsible for collecting, storing, and retrieving logs during pipeline execution. Let's take a deeper dive into the fundamentals behind its abstraction, namely the `BaseLogStore` class:

1. **Origins**: A `BaseLogStoreOrigin` represents the source of log records (e.g., a step execution). When logging starts, you register an origin with the log store, then emit logs through the log store referencing that origin. When logging ends, you deregister the origin to release resources.

2. **Core methods**: The base class defines four abstract methods that must be implemented:
   - `emit()`: Process and export a log record for a given origin
   - `_release_origin()`: Called when logging for an origin is complete (cleanup resources)
   - `flush()`: Ensure all pending logs are exported
   - `fetch()`: Retrieve stored logs for display

3. **Thread safety**: The base implementation includes locking mechanisms to ensure thread-safe operation.

Here's a simplified view of the base implementation:

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
import logging
import threading

from zenml.enums import StackComponentType
from zenml.models import LogsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils.logging_utils import LogEntry


class BaseLogStoreConfig(StackComponentConfig):
    """Base configuration for all log stores."""
    pass


class BaseLogStoreOrigin:
    """Represents the source of log records (e.g., a step execution)."""

    def __init__(
        self,
        name: str,
        log_store: "BaseLogStore",
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        self._name = name
        self._log_store = log_store
        self._log_model = log_model
        self._metadata = metadata

    @property
    def name(self) -> str:
        """The name of the origin."""
        return self._name

    @property
    def log_model(self) -> LogsResponse:
        """The log model associated with the origin."""
        return self._log_model

    @property
    def metadata(self) -> Dict[str, Any]:
        """The metadata associated with the origin."""
        return self._metadata

    def deregister(self) -> None:
        """Deregister the origin from the log store."""
        self._log_store.deregister_origin(self)


class BaseLogStore(StackComponent, ABC):
    """Base class for all ZenML log stores."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._origins: Dict[str, BaseLogStoreOrigin] = {}
        self._lock = threading.RLock()

    @property
    def origin_class(self) -> Type[BaseLogStoreOrigin]:
        """Class of the origin used with this log store."""
        return BaseLogStoreOrigin

    def register_origin(
        self, name: str, log_model: LogsResponse, metadata: Dict[str, Any]
    ) -> BaseLogStoreOrigin:
        """Register an origin for a logging context."""
        with self._lock:
            origin = self.origin_class(name, self, log_model, metadata)
            self._origins[name] = origin
            return origin

    def deregister_origin(self, origin: BaseLogStoreOrigin) -> None:
        """Deregister an origin and finalize its logs."""
        with self._lock:
            if origin.name not in self._origins:
                return
            self._release_origin(origin)
            del self._origins[origin.name]
            if len(self._origins) == 0:
                self.flush(blocking=False)

    @abstractmethod
    def emit(
        self,
        origin: BaseLogStoreOrigin,
        record: logging.LogRecord,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Process a log record for the given origin."""

    @abstractmethod
    def _release_origin(self, origin: BaseLogStoreOrigin) -> None:
        """Finalize logging for an origin and release resources."""

    @abstractmethod
    def flush(self, blocking: bool = True) -> None:
        """Flush all pending logs."""

    @abstractmethod
    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List[LogEntry]:
        """Fetch stored logs."""


class BaseLogStoreFlavor(Flavor):
    """Base class for all ZenML log store flavors."""

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        return BaseLogStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseLogStore"]:
        """Implementation class for this flavor."""
```

{% hint style="info" %}
This is a slimmed-down version of the base implementation. For the full implementation with complete docstrings, check the [SDK docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.base_log_store).
{% endhint %}

### Extending the OTEL Log Store

For most custom implementations, you'll want to extend `OtelLogStore` rather than `BaseLogStore` directly. The OTEL Log Store provides:

- OpenTelemetry infrastructure (LoggerProvider, BatchLogRecordProcessor)
- Automatic log batching and retry logic
- Standard OTEL log format conversion

To create a custom OTEL-based log store, you only need to implement:

1. `get_exporter()`: Return your custom log exporter
2. `fetch()`: Retrieve logs from your backend (optional, raise `NotImplementedError` if not supported)

```python
from typing import List, Optional, Type
from datetime import datetime

from opentelemetry.sdk._logs.export import LogExporter

from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig, OtelLogStoreFlavor
from zenml.models import LogsResponse
from zenml.utils.logging_utils import LogEntry


class MyLogStoreConfig(OtelLogStoreConfig):
    """Configuration for my custom log store."""
    
    my_custom_setting: str = "default_value"
    api_key: str  # Required setting


class MyLogStore(OtelLogStore):
    """Custom log store implementation."""

    @property
    def config(self) -> MyLogStoreConfig:
        return cast(MyLogStoreConfig, self._config)

    def get_exporter(self) -> LogExporter:
        """Return the log exporter for your backend."""
        return MyCustomLogExporter(
            endpoint=self.config.endpoint,
            api_key=self.config.api_key,
        )

    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List[LogEntry]:
        """Fetch logs from your backend."""
        # Implement log retrieval from your backend
        # Return a list of LogEntry objects
        raise NotImplementedError(
            "Log fetching is not supported by this log store."
        )


class MyLogStoreFlavor(OtelLogStoreFlavor):
    """Flavor for my custom log store."""

    @property
    def name(self) -> str:
        return "my_custom"

    @property
    def config_class(self) -> Type[MyLogStoreConfig]:
        return MyLogStoreConfig

    @property
    def implementation_class(self) -> Type[MyLogStore]:
        return MyLogStore
```

### Creating a Custom Log Exporter

If you're using a custom backend, you'll need to implement a log exporter. The exporter receives batches of OpenTelemetry log records and sends them to your backend:

```python
from typing import Sequence
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult


class MyCustomLogExporter(LogExporter):
    """Exporter that sends logs to my custom backend."""

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self._shutdown = False

    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        """Export a batch of logs."""
        if self._shutdown:
            return LogExportResult.FAILURE

        try:
            # Convert OTEL logs to your backend's format
            logs_data = []
            for log_data in batch:
                record = log_data.log_record
                logs_data.append({
                    "timestamp": record.timestamp,
                    "message": str(record.body),
                    "severity": record.severity_text,
                    "attributes": dict(record.attributes or {}),
                })

            # Send to your backend
            response = requests.post(
                self.endpoint,
                json={"logs": logs_data},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            
            if response.ok:
                return LogExportResult.SUCCESS
            return LogExportResult.FAILURE

        except Exception:
            return LogExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        self._shutdown = True
```

### Implementing Log Fetching

If your backend supports log retrieval, implement the `fetch()` method to enable log viewing in the ZenML dashboard:

```python
def fetch(
    self,
    logs_model: LogsResponse,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 20000,
) -> List[LogEntry]:
    """Fetch logs from the backend."""
    # Query your backend using logs_model.id to filter
    response = requests.get(
        f"{self.config.endpoint}/logs",
        params={
            "log_id": str(logs_model.id),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "limit": limit,
        },
        headers={"Authorization": f"Bearer {self.config.api_key}"},
    )
    
    log_entries = []
    for log in response.json()["logs"]:
        log_entries.append(LogEntry(
            message=log["message"],
            level=LoggingLevels[log["severity"].upper()],
            timestamp=datetime.fromisoformat(log["timestamp"]),
            name=log.get("logger_name"),
            filename=log.get("filename"),
            lineno=log.get("line_number"),
        ))
    
    return log_entries
```

### Build Your Own Custom Log Store

Follow these steps to create and register your custom log store:

1. **Create the implementation**: Implement your log store class, configuration, and flavor as shown above.

2. **Create the exporter** (if needed): Implement a custom `LogExporter` for your backend.

3. **Register the flavor**: Use the CLI to register your custom flavor:

```shell
zenml log-store flavor register <path.to.MyLogStoreFlavor>
```

For example, if your flavor class `MyLogStoreFlavor` is defined in `flavors/my_log_store.py`:

```shell
zenml log-store flavor register flavors.my_log_store.MyLogStoreFlavor
```

{% hint style="warning" %}
ZenML resolves the flavor class by taking the path where you initialized zenml (via `zenml init`) as the starting point of resolution. Ensure you follow [the best practice](https://docs.zenml.io/user-guides/best-practices/iac) of initializing zenml at the root of your repository.
{% endhint %}

4. **Verify registration**: Check that your flavor appears in the list:

```shell
zenml log-store flavor list
```

5. **Register and use your log store**:

```shell
zenml log-store register my_logs \
    --flavor=my_custom \
    --endpoint=https://my-backend.example.com/logs \
    --api_key=<MY_API_KEY>

zenml stack register my_stack -ls my_logs ... --set
```

{% hint style="info" %}
**Important timing notes:**

- The **CustomLogStoreFlavor** class is imported when registering the flavor via CLI.
- The **CustomLogStoreConfig** class is imported when registering/updating a stack component (used for validation).
- The **CustomLogStore** class is only imported when the component is actually used.

This separation allows you to register flavors even when their dependencies aren't installed locally.
{% endhint %}


{% hint style="warning" %}
**Important**: Log stores are instantiated on the ZenML server to fetch logs for display in the dashboard. This introduces a critical constraint on your implementation. When the ZenML dashboard or API requests logs, the server instantiates the log store and calls its `fetch()` method. This means that there can be **no external dependencies** that aren't already installed on the ZenML server.
{% endhint %}

### Best Practices

1. **Extend OtelLogStore**: Unless you have specific requirements, extend `OtelLogStore` to benefit from built-in batching and retry logic.

2. **Handle failures gracefully**: Log export failures shouldn't crash your pipeline. Return `LogExportResult.FAILURE` and log warnings.

3. **Implement retry logic**: For network-based backends, implement retry logic in your exporter.

4. **Use secrets for credentials**: Store API keys and tokens in ZenML secrets, not in the config directly.

5. **Test thoroughly**: Test your implementation with various log volumes and failure scenarios.

6. **Document configuration**: Clearly document all configuration options and their defaults.

7. **Keep fetch() simple**: Remember that `fetch()` runs on the server with limited dependencies. Use only built-in Python libraries and HTTP APIs.
