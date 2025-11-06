---
description: Developing a custom log store.
---

# Develop a Custom Log Store

If you want to send logs to a backend that isn't covered by the built-in log stores, you can create your own custom log store implementation.

### Base Abstraction

The `BaseLogStore` provides three main methods that you need to implement:

```python
import logging
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.models import LogsRequest

class MyLogStoreConfig(BaseLogStoreConfig):
    """Configuration for my custom log store."""
    
    my_setting: str
    another_setting: int = 100

class MyLogStore(BaseLogStore):
    """My custom log store implementation."""

    @property
    def config(self) -> MyLogStoreConfig:
        return cast(MyLogStoreConfig, self._config)

    def activate(self, log_request: LogsRequest) -> None:
        """Activate log collection.
        
        This is called at the start of a pipeline run or step.
        Set up your logging handlers, connections, and register
        with the routing handler.
        
        Args:
            log_request: Contains log ID, URI, and metadata.
        """
        from zenml.logging.routing_handler import (
            ensure_routing_handler_installed,
            set_active_log_store,
        )
        
        # Ensure global routing handler is installed
        ensure_routing_handler_installed()
        
        # Initialize your backend connection
        self._setup_backend(log_request)
        
        # Register this log store for current thread
        set_active_log_store(self)

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record.
        
        This is called by the routing handler for each log message.
        Send the log to your backend. You can safely use print()
        or logger.info() here - reentrancy protection prevents loops.
        
        Args:
            record: The log record to process.
        """
        # Send log to your backend
        self._send_to_backend(record)

    def deactivate(self) -> None:
        """Deactivate log collection and clean up.
        
        This is called at the end of a pipeline run or step.
        Flush any pending logs, close connections, and unregister.
        """
        from zenml.logging.routing_handler import set_active_log_store
        
        # Unregister from routing handler
        set_active_log_store(None)
        
        # Clean up your backend connection
        self._cleanup_backend()

    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List[LogEntry]:
        """Fetch logs from the backend.
        
        This is called by the server to retrieve logs for display.
        Query your backend and return logs as LogEntry objects.
        
        Args:
            logs_model: Contains pipeline_run_id, step_id, and metadata.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of logs to return.
            
        Returns:
            List of log entries.
        """
        return []
```

### Implementation Patterns

#### 1. Direct Implementation (Simple)

The simplest pattern is to directly implement the `emit()` method:

```python
import logging
from zenml.log_stores import BaseLogStore

class MyLogStore(BaseLogStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend_client = None

    def activate(self, log_request):
        from zenml.logging.routing_handler import (
            ensure_routing_handler_installed,
            set_active_log_store,
        )
        
        # Install routing handler
        ensure_routing_handler_installed()
        
        # Set up backend connection
        self.backend_client = MyBackendClient(
            url=self.config.backend_url,
            log_id=log_request.id,
        )
        
        # Register for current thread
        set_active_log_store(self)

    def emit(self, record):
        """Process each log record."""
        # You can safely use print() or logger.info() here!
        # Reentrancy protection prevents infinite loops.
        
        log_data = {
            "message": record.getMessage(),
            "level": record.levelname,
            "timestamp": record.created,
        }
        
        self.backend_client.send_log(log_data)

    def deactivate(self):
        from zenml.logging.routing_handler import set_active_log_store
        
        if self.backend_client:
            self.backend_client.close()
        
        set_active_log_store(None)
```

#### 2. Using Internal Handlers (Advanced)

If you want to use Python's logging.Handler internally:

```python
class MyLogStore(BaseLogStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handler = None

    def activate(self, log_request):
        from zenml.logging.routing_handler import (
            ensure_routing_handler_installed,
            set_active_log_store,
        )
        
        ensure_routing_handler_installed()
        
        # Create internal handler (not added to root logger)
        self._handler = MyCustomHandler(
            backend_url=self.config.backend_url,
            log_id=log_request.id,
        )
        
        set_active_log_store(self)

    def emit(self, record):
        """Delegate to internal handler."""
        if self._handler:
            self._handler.emit(record)

    def deactivate(self):
        from zenml.logging.routing_handler import set_active_log_store
        
        if self._handler:
            self._handler.flush()
            self._handler.close()
        
        set_active_log_store(None)
```

#### 3. Background Processing

For efficient log handling, use background threads for batching:

```python
import queue
import threading

class MyLogStore(BaseLogStore):
    def activate(self, log_request):
        from zenml.logging.routing_handler import (
            ensure_routing_handler_installed,
            set_active_log_store,
        )
        
        ensure_routing_handler_installed()
        
        self.log_queue = queue.Queue(maxsize=2048)
        self.shutdown_event = threading.Event()
        self.worker_thread = threading.Thread(
            target=self._process_logs,
            daemon=True
        )
        self.worker_thread.start()
        
        set_active_log_store(self)

    def emit(self, record):
        """Queue logs for background processing."""
        try:
            self.log_queue.put_nowait(record)
        except queue.Full:
            pass  # Drop logs if queue is full

    def _process_logs(self):
        """Background thread processes queued logs."""
        while not self.shutdown_event.is_set():
            try:
                record = self.log_queue.get(timeout=1)
                self._send_to_backend(record)
            except queue.Empty:
                continue

    def deactivate(self):
        from zenml.logging.routing_handler import set_active_log_store
        
        self.shutdown_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        set_active_log_store(None)
```

#### 4. Fetching Logs

Implement fetch using HTTP APIs or SDKs:

```python
import requests
from zenml.logging.step_logging import LogEntry

class MyLogStore(BaseLogStore):
    def fetch(
        self,
        logs_model,
        start_time=None,
        end_time=None,
        limit=20000,
    ):
        """Fetch logs from your backend."""
        query = {
            "pipeline_run_id": str(logs_model.pipeline_run_id),
        }
        
        if logs_model.step_run_id:
            query["step_id"] = str(logs_model.step_run_id)
        if start_time:
            query["start_time"] = start_time.isoformat()
        if end_time:
            query["end_time"] = end_time.isoformat()
            
        response = requests.post(
            f"{self.config.backend_url}/query",
            json=query,
            headers={"Authorization": f"Bearer {self.config.api_key}"}
        )
        
        logs = []
        for log_data in response.json()["logs"][:limit]:
            logs.append(LogEntry(
                message=log_data["message"],
                level=log_data.get("level"),
                timestamp=log_data.get("timestamp"),
            ))
        return logs
```

### Creating a Flavor

To make your log store usable via CLI, create a flavor:

```python
from zenml.enums import StackComponentType
from zenml.stack.flavor import Flavor

class MyLogStoreFlavor(Flavor):
    @property
    def name(self) -> str:
        return "my_custom_store"

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        from my_module import MyLogStoreConfig
        return MyLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        from my_module import MyLogStore
        return MyLogStore
```

Register your flavor:

```bash
zenml log-store flavor register my_module.MyLogStoreFlavor
```

Then use it:

```bash
zenml log-store register my_logs --flavor my_custom_store \
    --backend_url=https://logs.example.com \
    --api_key=secret
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

