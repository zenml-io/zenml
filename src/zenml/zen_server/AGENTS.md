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

## Standard Endpoint Pattern

Server endpoints follow a consistent pattern:

1. **Authorize** — call `authorize(...)` for authentication
2. **Entitlement check** — verify feature access if the endpoint is gated
3. **RBAC** — use `verify_permissions_and_*` wrappers or explicit permission checks
4. **Store operation** — call `zen_store()` for the actual data operation
5. **Async wrapper** — wrap with `async_fastapi_endpoint_wrapper` for async compatibility

Non-CRUD endpoints (e.g., trigger attach/detach) may require permission checks across multiple resource domains.

## FastAPI Agent Profile
- ZenML OSS FastAPI work demands senior-level proficiency across FastAPI, SQLModel, SQLAlchemy 2.0, and modern Pydantic v2 patterns; study existing routers and services before proposing changes.
- Favor object-oriented extensions over scattering helpers—extend service/repository classes or introduce cohesive new ones, and rely on dependency injection rather than module-level singletons.
- Keep all shared state inside FastAPI's dependency system or app factory; never introduce fresh global variables outside the initializer.
- Use descriptive auxiliary-verb-prefixed names and lower_snake_case paths (for example `routers/manage_invitation.py`, `services/issue_token.py`) so reviewers immediately understand intent.
- Apply the Receive an Object, Return an Object (RORO) convention on public interfaces to keep payloads self-documenting and testable.

## FastAPI Project Structure
- Each FastAPI package must expose a router entry point plus clearly separated sub-routes, utilities, static assets, and schema/model definitions; keep imports explicit via named exports.
- Co-locate Pydantic request/response models with their consuming routes, and keep reusable business logic inside services or repositories accessed through dependency injection.
- Name directories/files with verbs or nouns that communicate behavior (e.g., `routers/register_user.py`, `services/create_invitation.py`) so navigation stays predictable.

## FastAPI Error Handling & Validation
- Lead with guard clauses in routes, dependencies, and services—validate payloads, auth context, and resources early; prefer early returns and keep the happy path last.
- Skip redundant `else` blocks after returns; log context-rich errors and surface user-safe details while retaining debug information in structured logs.
- Define custom exception types or factories so middleware can map them to consistent JSON payloads with trace metadata.
- Raise `HTTPException` (with precise status codes and detail strings) for expected errors, and push unexpected failures through middleware that centralizes logging, metrics, and alerting.
- Model inputs/outputs with Pydantic BaseModel derivatives to keep validation explicit and documentation synchronized automatically.
