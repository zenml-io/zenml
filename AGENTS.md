# ZenML Codex Agent Guidelines

ZenML is an extensible open-source MLOps framework for creating production-ready
ML pipelines. This root guide contains rules that must be loaded for every
Codex session in this repository. For detailed workflows, examples, and
subsystem recipes, use `.agents/skills/zenml-repo-workflows/SKILL.md`.

## Project Structure

- `src/zenml/` - Core source code.
- `tests/` - Unit and integration tests.
- `docs/book/` - Source documentation.
- `examples/` - Example projects.
- `scripts/` - Development utilities.

## Always-Loaded Rules

- Use US English spelling in code, comments, docstrings, and documentation.
- Use Python 3.10+ compatible code.
- Type hint function parameters and return values.
- Follow Google Python style for docstrings. Include `Args`, `Returns`,
  `Yields`, and `Raises` sections whenever the function contract requires them;
  do not use a summary-only docstring to omit applicable sections.
- Prefer clear names and small functions over explanatory comments.
- Comments should explain intent, trade-offs, constraints, invariants, and
  tricky edge cases. Avoid comments that restate obvious code.
- Do not use multi-line banner comments to group classes or functions.
- Prefer typed contracts over `getattr`/`hasattr` capability checks when static
  typing can express the requirement.
- Private methods and functions with a leading underscore should not be called
  outside their class or module.
- Integrations should avoid using ZenML private methods because externalized
  integrations will not be protected by in-repo type checks.

## Common Commands

- Format before committing: `bash scripts/format.sh`.
- Check quality: `bash scripts/lint.sh`.
- Run targeted tests only: `pytest tests/unit/path/to/test_file.py` or
  `pytest tests/unit/path/to/test_file.py::test_specific_function`.
- Do NOT run the entire local test suite by default; many tests need special
  environments.
- If you make changes after running tests, rerun the relevant tests.

## Branches, Git, and PRs

- `develop` is the primary working branch, not `main`.
- Always branch off `develop` for new work.
- PRs should target `develop`.
- `main` is only updated during releases.
- Use targeted `git add`; do not stage unrelated files.
- Never add anything from `design/` to git history.
- PR titles should be concise and human-readable, without prefixes like
  `feat:`.
- Every PR must have exactly one release-notes label:
  `release-notes` or `no-release-notes`.
- When pushing new commits to an open PR, check whether the PR description needs
  updating.

## Security

- NEVER commit secrets, API keys, tokens, passwords, or credentials.
- Use environment variables or ZenML secret management for sensitive data.
- Validate and sanitize user inputs.
- If secrets are accidentally committed, notify the team immediately.

## Architecture and API Safety

- Check whether a class or function is exported in `zenml.__init__` before
  changing a public-looking interface.
- Public APIs need backward-compatible evolution or deprecation.
- For internal non-underscore methods, search for usages and update all
  internal callers.
- The term "model" can mean Pydantic models, machine learning models, or ZenML
  model namespaces. Be explicit when writing or reviewing.
- When changing cross-cutting features, trace the full path through CLI,
  client, server, models, schemas, migrations, tests, and docs.

## FastAPI and Runtime Rules

- ZenML OSS FastAPI work expects FastAPI, SQLModel, SQLAlchemy 2.0, and
  Pydantic v2 patterns.
- Implement synchronous `def` route handlers for OSS Codex contributions.
- Keep shared state inside FastAPI dependency injection or the application
  factory; never introduce fresh global variables outside initialization.
- Start routes, dependencies, and services with guard clauses.
- Raise `HTTPException` with precise status codes for expected errors.
- Use Pydantic models for route inputs and outputs.
- When changing server framework (e.g., `fastapi`) or database library versions,
  check whether related OpenTelemetry SDK, exporter, and instrumentation
  dependencies also need updates. Breaking changes in instrumented libraries can
  require coordinated OTel updates. Keep OTel SDK/exporter versions aligned with
  the matching OpenTelemetry instrumentation beta line.
- Code outside `src/zenml/zen_server/` should NEVER import from `zen_server/`.

## Database and Storage Rules

- ZenML uses SQLModel and SQLAlchemy; no raw SQL unless absolutely necessary.
- Database schema changes require Alembic migrations.
- Never modify existing migrations that are already on `main` or `develop`.
- Always consider backward compatibility for rolling deployments.
- Test migration upgrade paths with `alembic upgrade head` for meaningful
  schema changes.
- Code outside `zen_stores/` should not import SQL-related code directly from
  `zen_stores`; use `Client` or, rarely, `client.zen_store`.

## Subsystem Pointers

Load `.agents/skills/zenml-repo-workflows/SKILL.md` for detailed guidance on
tests, PRs, migrations, docs, integrations, models, orchestrators, FastAPI,
server code, and storage.

Directory-specific reminders:

- `docs/book/AGENTS.md` - documentation source, GitBook links, and docs checks.
- `src/zenml/cli/AGENTS.md` - CLI import rules and filter/client coupling.
- `src/zenml/integrations/AGENTS.md` - integration flavor import rules.
- `src/zenml/models/AGENTS.md` - domain model compatibility and filter fields.
- `src/zenml/orchestrators/AGENTS.md` - orchestrator IDs and dynamic pipelines.
- `src/zenml/zen_server/AGENTS.md` - server import boundary and endpoint shape.
- `src/zenml/zen_stores/migrations/AGENTS.md` - Alembic migration guidance.
- `src/zenml/zen_stores/schemas/AGENTS.md` - ORM schema and SQL import rules.

## Reviewer Checklist

- Integration PRs: no top-level integration-library imports in flavor files.
- Orchestrator PRs: `get_orchestrator_run_id` is unique per run and stable for
  all steps in that run.
- Filter model changes: matching client method signature and body are updated.
- Private method changes: all internal usages are updated.
- Import checks: no `zen_server` imports outside `zen_server`.
- Import checks: no direct SQL imports outside `zen_stores`.
- Model changes: adding properties is usually OK; deleting, renaming, or
  incompatible type changes are risky.
- Dependency bumps: dropping old version support is breaking.
- Scheduling changes: check both legacy schedule and trigger stacks.
- Step operator changes: check `BaseStepOperator`, `StepLauncher`, and at least
  one concrete integration.

## Documentation Rules

- Documentation source files live in `docs/book/`.
- Do not edit generated docs directories such as `docs/mkdocs/` or
  `docs/site/`.
- When adding or removing docs pages, update the relevant `toc.md`.
- Assets belong in a `.gitbook` folder beside the relevant `toc.md`.

For human contributors, see `CONTRIBUTING.md`.
