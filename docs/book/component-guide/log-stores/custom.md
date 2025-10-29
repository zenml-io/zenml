---
description: Developing a custom log store.
---

# Develop a Custom Log Store

If you want to send logs to a backend that isn't covered by the built-in log stores, you can create your own custom log store implementation.

### Base Abstraction

The `BaseLogStore` provides three main methods that you need to implement:

```python
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig

class MyLogStoreConfig(BaseLogStoreConfig):
    """Configuration for my custom log store."""
    
    my_setting: str
    another_setting: int = 100

class MyLogStore(BaseLogStore):
    """My custom log store implementation."""

    @property
    def config(self) -> MyLogStoreConfig:
        return cast(MyLogStoreConfig, self._config)

    def activate(
        self,
        pipeline_run_id: UUID,
        step_id: Optional[UUID] = None,
        source: str = "step",
    ) -> None:
        """Activate log collection.
        
        This is called at the start of a pipeline run or step.
        Set up your logging handlers, connections, and any
        background processing here.
        """
        pass

    def deactivate(self) -> None:
        """Deactivate log collection and clean up.
        
        This is called at the end of a pipeline run or step.
        Flush any pending logs, close connections, and clean
        up resources here.
        """
        pass

    def fetch(
        self,
        pipeline_run_id: UUID,
        step_id: Optional[UUID] = None,
        source: Optional[str] = None,
        logs_uri: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List[LogEntry]:
        """Fetch logs from the backend.
        
        This is called by the server to retrieve logs for display.
        Query your backend and return logs as LogEntry objects.
        """
        return []
```

### Implementation Patterns

#### 1. Using Python Logging Handlers

The most common pattern is to create a `logging.Handler` that sends logs to your backend:

```python
import logging
from zenml.log_stores import BaseLogStore
from zenml.logger import logging_handlers, get_storage_log_level

class MyLogStore(BaseLogStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = None
        self._original_root_level = None

    def activate(self, pipeline_run_id, step_id=None, source="step"):
        self.handler = MyCustomHandler(
            backend_url=self.config.backend_url,
            pipeline_run_id=pipeline_run_id,
            step_id=step_id,
        )
        
        self.handler.setLevel(get_storage_log_level().value)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(self.handler)
        
        self._original_root_level = root_logger.level
        handler_levels = [h.level for h in root_logger.handlers]
        root_logger.setLevel(min(handler_levels))
        
        logging_handlers.add(self.handler)

    def deactivate(self):
        if not self.handler:
            return
            
        root_logger = logging.getLogger()
        if self.handler in root_logger.handlers:
            root_logger.removeHandler(self.handler)
            
        if self._original_root_level is not None:
            root_logger.setLevel(self._original_root_level)
            
        logging_handlers.remove(self.handler)
```

#### 2. Background Processing

For efficient log handling, use background threads or async processing:

```python
import queue
import threading

class MyLogStore(BaseLogStore):
    def activate(self, pipeline_run_id, step_id=None, source="step"):
        self.log_queue = queue.Queue(maxsize=2048)
        self.shutdown_event = threading.Event()
        self.worker_thread = threading.Thread(
            target=self._process_logs,
            daemon=True
        )
        self.worker_thread.start()

    def _process_logs(self):
        while not self.shutdown_event.is_set():
            try:
                log_entry = self.log_queue.get(timeout=1)
                self._send_to_backend(log_entry)
            except queue.Empty:
                continue

    def deactivate(self):
        self.shutdown_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
```

#### 3. Fetching Logs

Implement fetch using HTTP APIs or SDKs:

```python
from zenml.logging.step_logging import LogEntry

class MyLogStore(BaseLogStore):
    def fetch(
        self,
        pipeline_run_id,
        step_id=None,
        source=None,
        logs_uri=None,
        start_time=None,
        end_time=None,
        limit=20000,
    ):
        query = {
            "pipeline_run_id": str(pipeline_run_id),
        }
        if step_id:
            query["step_id"] = str(step_id)
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

