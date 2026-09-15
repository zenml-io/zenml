# ZenML Server Agent Guidelines

This file applies to changes in `src/zenml/zen_server/` and below. For
detailed FastAPI guidance, use the repo-root
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Critical Import Boundary

Code outside `src/zenml/zen_server/` should NEVER import from `zen_server/`.

Server dependencies such as FastAPI and uvicorn are optional in many client
installations. If client code imports server code, it can fail on machines that
do not have server dependencies installed.

Allowed:

- Server code importing within `zen_server/`.
- Client-side code using shared models from `src/zenml/models/`.
- Client-side code using the `Client` abstraction for server communication.

## Endpoint Pattern

Most server endpoints follow this order:

1. Authorize.
2. Check entitlements when feature access is gated.
3. Verify RBAC permissions.
4. Call `zen_store()` for the data operation.

Ordinary store-backed handlers use synchronous `def` with
`async_fastapi_endpoint_wrapper`, as neighboring routes do. Keep async handlers
when they await request-body access or other I/O. For example, webhook intake
awaits the raw body and uses `run_in_threadpool` for synchronous processing;
do not move blocking store work onto the event loop.

Non-CRUD endpoints, such as trigger attach/detach, may need permission checks
across multiple resource domains.

When calling any `zen_store().list_*` method for a project-scoped resource,
always set `project=...` on the filter. A list call without project scope
queries across all projects.

## FastAPI Rules

- Prefer existing service or repository classes over scattered helpers.
- Keep shared state inside dependency injection or the app factory.
- Never introduce fresh global variables outside initialization.
- Lead with guard clauses for auth, payload, dependency, and resource checks.
- Raise `HTTPException` with precise status codes for expected failures.
- Use Pydantic models for route inputs and outputs.
