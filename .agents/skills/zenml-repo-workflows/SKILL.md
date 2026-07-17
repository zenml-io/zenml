---
name: zenml-repo-workflows
description: Use for ZenML repo work involving tests, PRs, migrations, docs, integrations, models, orchestrators, server, or storage.
---

# ZenML Repo Workflows

Use this skill when work in the ZenML repository needs more detail than the
always-loaded `AGENTS.md` files provide. The root guide keeps safety rules,
universal conventions, and the most common commands in memory. This skill keeps
the longer recipes, examples, and subsystem checklists.

## Moved Content Index

Former root headings covered here:

- Code Style & Quality Standards
- Commenting policy
- Formatting and Linting
- Python Standards
- Util Function Placement
- Private Methods and API Stability
- FastAPI Agent Profile
- FastAPI Project Structure
- Prefer typing over dynamic attribute checks
- Error Handling & Validation
- Testing Requirements
- Dependencies & Runtime Constraints
- Development Workflow
- Prerequisites
- Documentation Access via MCP
- Environment Variables
- Branch Management
- Making Changes
- Security Guidelines
- Database and Migration Guidelines
- Migration Testing Workflow
- Commit Message Guidelines
- When Implementing Features
- When Fixing Bugs
- Pull Request Guidelines
- Continuous Integration
- Core Concepts
- Important Terminology
- Pipeline Architecture
- Key Abstractions
- Cross-Cutting Architecture Areas
- Common Tasks
- Adding New Integrations
- Modifying Core Functionality
- Expert Tips
- Summary Checklist for PR Reviewers
- Documentation Guidelines
- Structure
- Format and Style
- Content Standards

## Development Workflow

### Setup

- Install ZenML in development mode with dev dependencies.
- ZenML recommends `uv` for Python package installation because it resolves
  dependencies more quickly and reliably than plain `pip`.
- Useful development environment variables:
  - `ZENML_LOGGING_VERBOSITY=DEBUG`
  - `MLSTACKS_ANALYTICS_OPT_OUT=true`
  - `AUTO_OPEN_DASHBOARD=false`
  - `ZENML_ENABLE_RICH_TRACEBACK=false`
  - `TOKENIZERS_PARALLELISM=false`
- Always set the following environment variables when developing:
  - `ZENML_ANALYTICS_OPT_IN=false`: Disables analytics during development
  - `ZENML_DEBUG=true`: Uses the development ZenML analytics server to avoid
    sending analytics to the official ZenML analytics server (IMPORTANT!). This
    must be set even if `ZENML_ANALYTICS_OPT_IN=true` because in a client-server
    setup, the server controls the client-side analytics opt-in status.

### Formatting, Linting, and Tests

- Format before committing: `bash scripts/format.sh`.
- Check quality: `bash scripts/lint.sh`.
- The lint script runs Ruff, pydoclint on `src/zenml tests/harness`, yamlfix,
  zizmor, unused import/variable checks, Ruff formatting checks, and mypy.
- Full mypy is slow on the whole codebase. For focused work, run mypy on the
  changed file or package.
- Run targeted pytest files or tests for the component you changed. Avoid the
  full local test suite unless there is a specific reason.
- Some coverage workflows use `bash scripts/test-coverage-xml.sh`, but that does
  not run every test.

### Branches and PRs

- `develop` is the primary working branch. PRs should target `develop`.
- `main` is only updated during the release process.
- PR titles should be human-readable and concise. Avoid prefixes like `feat:`.
- PR descriptions should explain what changed, why it was needed, important
  implementation decisions, and anything reviewers should inspect carefully.
- Every PR needs exactly one release-notes label:
  - `release-notes` for user-facing features, API changes, important fixes, or
    changes users should know about.
  - `no-release-notes` for internal work, CI fixes, refactors, minor docs-only
    changes, or maintenance work.

### Continuous Integration

ZenML uses a two-tier CI setup:

- Fast CI runs on all PRs and covers basic tests, linting, and type checking.
- Full CI includes integration tests and broader coverage.
- The `run-slow-ci` label triggers full CI. Maintainers add it when required.
- If changes touch integrations or core behavior, mention in the PR that full
  CI should run.
- For GitHub Actions debugging, check whether logs have expired before deep
  investigation. If logs are expired, inspect current workflow files and recent
  runs instead.

## Code Style Details

### Comments

Use comments to explain intent, trade-offs, invariants, and edge cases. Prefer
clear names and small functions over comments that restate the code.

Good comments answer questions such as:

- Why is this constraint here?
- What edge case is being protected?
- Which external API behavior forced this shape?
- What invariant must future edits preserve?

Avoid:

- Change-tracking comments such as "updated from previous version".
- Comments that repeat the line below them.
- Multi-line banner comments grouping classes or functions.

### Python

- Use Python 3.10+ compatible code.
- Follow Google Python style for docstrings. Include `Args`, `Returns`,
  `Yields`, and `Raises` sections whenever the function contract requires them;
  do not use a summary-only docstring to omit applicable sections.
- Type hint function parameters and return values.
- Use descriptive names.
- Keep functions manageable. A 50-line target is useful, though not absolute.
- Prefer functional style where it fits the existing code.

### Helper Placement

Put a helper on a class when it only makes sense in that class context or when
subclasses call it frequently. Use a utility module for generic behavior shared
across unrelated modules.

Example: `BaseOrchestrator.requires_resources_in_orchestration_environment`
could be a global helper, but it lives on `BaseOrchestrator` because
orchestrator subclasses call it often and the behavior is part of orchestrator
execution decisions.

Useful utility locations:

- `src/zenml/utils/`
- `src/zenml/orchestrators/utils.py`
- `src/zenml/orchestrators/step_run_utils.py`
- `src/zenml/orchestrators/publish_utils.py`

### Private Methods and API Stability

Symbols with a leading underscore are private and should only be called from
inside their class or module.

When changing a non-underscore symbol, check whether it is exported from
`zenml.__init__`. Root exports and public methods on those exports are public
API and generally require deprecation before breaking changes.

Internal non-underscore code that is not exported at the root can usually be
changed without deprecation, but update all internal usages.

Integrations should avoid ZenML private methods because future external
integration packages will not be protected by in-repo mypy checks.

### Prefer Typing Over Dynamic Attribute Checks

Prefer `Protocol`, ABCs, `Union` with `isinstance` narrowing, or typed adapters
over `getattr`/`hasattr` for capability checks. Use dynamic attribute checks
only when the object is truly untyped, and isolate that behavior in a small
typed helper.

## FastAPI and Server Work

ZenML OSS FastAPI work expects strong FastAPI, SQLModel, SQLAlchemy 2.0, and
Pydantic v2 judgment.

Preferred patterns:

- Extend existing service or repository classes when behavior belongs there.
- Keep shared state in FastAPI dependency injection or the application factory.
- Use synchronous `def` route handlers in OSS Codex contributions.
- Use descriptive lower_snake_case paths and named exports.
- Co-locate Pydantic request/response models with consuming routes.
- Keep reusable behavior in service or repository modules accessed through
  dependency injection.
- Start routes, dependencies, and services with guard clauses.
- Avoid redundant `else` blocks after returns.
- Raise `HTTPException` with precise status codes for expected failures.
- Let middleware translate unexpected failures into consistent JSON responses
  with logging and metrics.
- Define inputs and outputs with Pydantic models so validation and docs stay in
  sync.

Import rule: code outside `src/zenml/zen_server/` must not import from
`zen_server/`. Client-side code should use `Client` and shared models from
`src/zenml/models/`.

## Database and Migrations

ZenML uses SQLModel and SQLAlchemy. Avoid raw SQL unless it is genuinely needed.

Database schema changes require Alembic migrations.

Migration rules:

- Create descriptive migrations, e.g. `alembic revision -m "Add X to Y table"`.
- Test upgrade paths with `alembic upgrade head`.
- Downgrade testing is optional because ZenML generally does not support
  downgrades.
- Never modify existing migrations that are already on `main` or `develop`.
- Consider rolling-deployment compatibility.
- Include schema changes and data migrations when both are needed.
- Run `scripts/check-alembic-branches.sh` to verify migration consistency.

Migration testing workflow:

1. Check out `develop` or the relevant old release.
2. Populate the database from that version.
3. Switch to the feature branch.
4. Run `alembic upgrade head`.

Useful MySQL query for foreign key dependency tracing:

```sql
SELECT
  kcu.CONSTRAINT_NAME AS fk_name,
  kcu.TABLE_SCHEMA AS referencing_schema,
  kcu.TABLE_NAME AS referencing_table,
  kcu.COLUMN_NAME AS referencing_column,
  kcu.REFERENCED_TABLE_SCHEMA AS referenced_schema,
  kcu.REFERENCED_TABLE_NAME AS referenced_table,
  kcu.REFERENCED_COLUMN_NAME AS referenced_column,
  rc.UPDATE_RULE,
  rc.DELETE_RULE
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND rc.CONSTRAINT_NAME  = kcu.CONSTRAINT_NAME
WHERE kcu.REFERENCED_TABLE_SCHEMA = '<DB_NAME>'
  AND kcu.REFERENCED_TABLE_NAME IN ('table1', 'table2')
ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION;
```

Use it before adding cascade behavior, dropping columns/tables, debugging FK
failures, or auditing existing delete rules.

## Documentation Work

Documentation content lives in `docs/book/`. Generated docs directories such as
`docs/mkdocs/` and `docs/site/` are not edit targets.

GitBook URLs follow the table of contents, not direct file paths. Pro docs under
`docs/book/getting-started/zenml-pro/` are served under
`https://docs.zenml.io/pro/...`.

When adding or removing docs pages, update the relevant `toc.md`. Assets belong
in a `.gitbook` folder beside the relevant `toc.md`.

Before committing docs changes with absolute URLs:

1. Check whether the URL exists.
2. Compare with existing working links in the same section.
3. Inspect the relevant `toc.md` to understand the public URL.

Link checking:

- `scripts/check_broken_links.py` and `scripts/check_relative_links.py` check
  relative markdown links.
- Lychee covers local files, images, HTML links, and external URLs.
- Local full docs check: `lychee --no-progress 'docs/book/**/*.md'`.
- Offline local links only: `lychee --offline --no-progress 'docs/book/**/*.md'`.

## Domain Models

Models live under `src/zenml/models`.

Core concepts:

- Requests, Updates, and typed Responses use Body, Metadata, and Resources.
- Filters provide typed operations, scoping, sorting, and pagination.
- Domain models must stay aligned with ORM schemas.
- Canonical Cursor rules live in `.cursor/rules/zenml-domain-models.mdc` and
  `.cursor/rules/zenml-orm-schema.mdc`.

Common base patterns:

- `BaseRequest` -> `{Entity}Request`
- `BaseUpdate` -> `{Entity}Update`
- `BaseResponse[Body, Metadata, Resources]`
- `BaseFilter`, `UserScopedFilter`, `ProjectScopedFilter`, `TaggableFilter`

Adding a new entity usually means implementing Request, ResponseBody,
ResponseMetadata, ResponseResources, Response, and Filter classes. Choose the
narrowest scope that matches ownership semantics.

### Filter Field Coupling

When adding a field to a filter model, update three locations:

1. The filter model field.
2. The corresponding `Client` list method signature.
3. The filter model instantiation inside that client method.

If the field should not become a CLI option, add it to `CLI_EXCLUDE_FIELDS`.

Test the new filter through the CLI, for example:

```bash
zenml pipeline runs list --new_field=some_value
```

Relationship-backed filter fields can also require custom ORM join behavior in
the store layer.

### Model Compatibility

Usually safe:

- Adding optional properties.

Risky or breaking:

- Deleting properties.
- Renaming properties.
- Making required fields optional in a way older code cannot tolerate.
- Changing property types.

Safe evolution pattern: add optional fields, deprecate before removal, use
defaults when adding required behavior, and consider versioned responses for
major changes.

## CLI Work

Important files:

- `src/zenml/cli/utils.py` for `list_options`.
- `src/zenml/cli/pipeline.py` for pipeline, run, legacy schedule, and
  replay/resume commands.
- `src/zenml/cli/trigger.py` for native trigger commands.
- `src/zenml/cli/resource_pool.py` and `resource_request.py` for resource pool
  and queue inspection commands.
- `src/zenml/cli/stack.py` for stack management.
- `src/zenml/cli/base.py` for core CLI setup and common decorators.

List commands use `@list_options(FilterModel)` to generate options from filter
model fields, then pass them to explicit client method parameters. If a field is
missing from the client method, the CLI can raise:

```text
TypeError: list_pipeline_runs() got an unexpected keyword argument 'new_field'
```

Scheduling command families:

- `zenml pipeline schedule ...` for legacy schedule records.
- `zenml trigger schedule ...` for native schedule triggers.
- `zenml trigger platform-event ...` for platform event triggers.

Resource pools use both management commands and request/queue inspection
commands. Check `ResourcePool*`, `ResourcePoolSubjectPolicy*`, and
`ResourceRequest*` models when editing this area.

Import rules:

- Do not import integration libraries at module level in CLI files.
- Do not import from `zen_server/` in CLI code.
- Do not import SQL schemas directly from `zen_stores/`; use `Client`.

## Integrations

The most important integration rule: flavor files must not import integration
libraries at module level.

Flavor files live at `src/zenml/integrations/*/flavors/*.py`. They are imported
for component discovery, so optional third-party libraries must only be imported
inside methods or under `TYPE_CHECKING`.

Correct pattern:

```python
from typing import TYPE_CHECKING, Type

from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.aws.orchestrators import SagemakerOrchestrator


class SagemakerOrchestratorFlavor(BaseOrchestratorFlavor):
    @property
    def implementation_class(self) -> Type["SagemakerOrchestrator"]:
        from zenml.integrations.aws.orchestrators import SagemakerOrchestrator

        return SagemakerOrchestrator
```

Integration package shape:

```text
src/zenml/integrations/<name>/
├── __init__.py
├── flavors/
├── orchestrators/
├── step_operators/
├── materializers/
└── ...
```

Step operators should implement the async-first lifecycle:

- `submit(...)`
- `get_status(...)`
- `wait(...)`
- `cancel(...)`

`StepLauncher` calls `submit()` plus `wait()` by default and falls back to
legacy `launch()` only for backwards compatibility. Store backend job IDs in run
metadata immediately after submission.

Dependency updates:

- Prefer inclusive lower bounds and exclusive upper bounds.
- Check Python version compatibility.
- Test locally with realistic integration scenarios.
- Treat dropping support for an old version as breaking.
- Mention breaking dependency changes in release notes.

## Orchestrators

Key files:

- `base_orchestrator.py`
- `containerized_orchestrator.py`
- `utils.py`
- `step_launcher.py`
- `step_runner.py`
- `cache_utils.py`, `input_utils.py`, `publish_utils.py`

Main submission methods:

- `submit_pipeline(...)` for static pipelines.
- `submit_dynamic_pipeline(...)` for dynamic pipelines.
- Isolated-step APIs for dynamic pipeline support:
  - `submit_isolated_step(...)`
  - `get_isolated_step_status(...)`
  - `wait_for_isolated_step(...)`
  - `stop_isolated_step(...)`

`BaseOrchestrator.run(...)` already prunes steps skipped by replay or
client-side caching before submission. Integration orchestrators should not
re-implement that pruning.

### `get_orchestrator_run_id`

This method must return an ID that is unique per backend run and stable for all
steps in the same ZenML pipeline run.

Static pipelines often start directly with the first step. The first step uses
the orchestrator run ID to create the ZenML run, and downstream steps use the
same ID to find it.

Dynamic pipelines have an initial orchestration container. Use an ID that is
stable for retries of that orchestration environment.

Kubernetes is special because it has an orchestration container even for static
pipelines. Prefer the configured Kubernetes run ID for static pipelines and the
parent Kubernetes job name for dynamic pipelines, falling back only when the job
lookup fails.

Implementation checklist:

- Inherit from `ContainerizedOrchestrator` if steps run in containers.
- Implement `get_orchestrator_run_id()` correctly.
- Implement `submit_pipeline()` for static pipelines.
- Implement `submit_dynamic_pipeline()` when supporting dynamic pipelines.
- Add isolated-step methods when needed.
- Handle scheduling hooks when the backend supports scheduling.
- Respect CPU, memory, GPU, and other resource settings.
- Return `SubmissionResult` with `wait_for_completion` for synchronous
  execution.
- Use `self.get_image(deployment, step_name)`.
- Use `orchestrator_utils.get_step_entrypoint_command(...)`.

## ORM Schemas and Zen Stores

ORM schemas live under `src/zenml/zen_stores/schemas`.

Rules:

- Use SQLModel declarative table classes.
- Prefer `BaseSchema` or `NamedSchema`.
- Keep fields aligned with domain models.
- Schema changes usually require migrations.
- Export new schemas from `src/zenml/zen_stores/schemas/__init__.py`.
- General string column limit is about 250 characters because of MySQL.

Foreign keys:

- Use `schema_utils.build_foreign_key_field`.
- Define relationships on both sides with matching `back_populates`.
- For many-to-many relationships, use a link model with composite primary keys.

Conversions:

- Provide `to_model`.
- Provide `from_request` or `from_model` where appropriate.
- Provide `update` or `update_from_model`.
- Include related resources only when requested by flags.
- Refresh `updated` on mutations.

Eager-loading rules:

- Collections use `selectinload`; `joinedload` on collections multiplies rows.
- Single-valued relationships use `joinedload` for get paths when the related
  row usually exists.
- Keep `selectinload` for nullable FKs that are usually empty.

Import rule: code outside `zen_stores/` should not import SQL-related code
directly from this directory. Use `Client`, or `client.zen_store` when lower
level access is truly needed.

## Cross-Area Change Checklist

Some features span many layers. When touching these, trace the whole path:

- Dynamic pipelines and nested child pipelines:
  - `src/zenml/execution/pipeline/dynamic/`
  - `src/zenml/pipelines/dynamic/`
  - orchestrators and `step_launcher.py`
  - pipeline run models, schemas, migrations, tests, and docs
- Triggers:
  - `src/zenml/triggers/`
  - trigger models, schemas, CLI, client, server endpoints, docs
- Resource pools and requests:
  - `src/zenml/models/v2/core/resource_pool*.py`
  - `resource_request.py`
  - `src/zenml/zen_stores/resource_pools/`
  - CLI, store behavior, Pro/backend scheduling behavior
- Container engines:
  - use `src/zenml/container_engines/` instead of direct Docker-specific calls

## Review Checklist

- Integration PRs: no library imports in flavor files.
- Orchestrator PRs: `get_orchestrator_run_id` is unique per run and stable for
  all steps in that run.
- Filter model changes: matching client method signature and body are updated.
- Private method changes: all internal usages are updated.
- Import checks: no `zen_server` imports outside `zen_server`.
- Import checks: no direct SQL imports outside `zen_stores`.
- Model changes: adding properties is usually OK; deleting, renaming, or
  incompatible type changes are risky.
- Dependency bumps: dropping old version support is breaking.
- Scheduling changes: update both legacy schedule and trigger stacks where
  relevant.
- Step operator changes: check `BaseStepOperator`, `StepLauncher`, and at least
  one concrete integration.
