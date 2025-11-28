# ZenML Server — Agent Guidelines

Guidance for agents working with ZenML server code.

## ⚠️ CRITICAL: Import Boundary

**Rule:** Code outside `zen_server/` should **NEVER** import from `zen_server/`

```
src/zenml/zen_server/   ← Server code (this directory)
src/zenml/...           ← Client code (everything else)
```

### Why This Matters

1. **Optional installation**: The ZenML server is not installed on client machines in most deployments
2. **Optional dependencies**: Server-specific dependencies (FastAPI, uvicorn, etc.) are only installed when users want to run a local server
3. **Import failures**: If client code imports from `zen_server/`, it will fail on machines without server dependencies

### What This Means

| From | Can import from `zen_server/`? |
|------|-------------------------------|
| `src/zenml/zen_server/*` | ✅ Yes |
| `src/zenml/client.py` | ❌ No |
| `src/zenml/cli/*` | ❌ No |
| `src/zenml/integrations/*` | ❌ No |
| Any other ZenML code | ❌ No |

### Correct Patterns

```python
# ❌ Bad - importing server code from client code
from zenml.zen_server.routers import pipeline_router
from zenml.zen_server.utils import server_config

# ✅ Good - use the Client abstraction instead
from zenml.client import Client
client = Client()
# The client handles all communication with the server
```

### If You Need Server Functionality

If you're writing code that needs to interact with server functionality:

1. **From client code**: Use the `Client` class which handles REST API communication
2. **From server code**: You can import freely within `zen_server/`
3. **Shared types**: Use models from `src/zenml/models/` which are shared between client and server
