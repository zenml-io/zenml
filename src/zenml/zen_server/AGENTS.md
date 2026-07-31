# ZenML Server Agent Guidelines

This file applies when Codex starts in `src/zenml/zen_server/` or below. For
detailed FastAPI guidance, use `.agents/skills/zenml-repo-workflows/SKILL.md`.

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
5. Use the async compatibility wrapper where existing routes do so.

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
