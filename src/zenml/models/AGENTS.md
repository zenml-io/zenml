# ZenML Domain Models Agent Guidelines

This file applies to changes in `src/zenml/models/` and below. For
detailed model hierarchy notes and examples, use
the repo-root `.agents/skills/zenml-repo-workflows/SKILL.md`.

Models live under `src/zenml/models`. Keep them aligned with ORM schemas and
store behavior.

## Core Patterns

- Requests represent creation payloads.
- Updates represent partial modification payloads.
- Responses use Body, Metadata, and Resources.
- Filters define query fields, operations, sorting, scoping, and pagination.
- Choose the narrowest scope that matches ownership semantics: global, user, or
  project.

## Cross-Layer Families

Trace the full path when touching:

- Triggers and schedule/platform event trigger models.
- Resource pools, subject policies, and resource requests.
- Run wait conditions.
- Nested child pipeline run fields such as `parent_run_id`, `child_key`, and
  `root_run_id`.

These often require aligned changes in CLI, client methods, server endpoints,
schemas, migrations, tests, and docs.

## Filter Field Checklist

When adding a filter field, update:

1. The filter model.
2. The corresponding `Client` list method signature.
3. The filter model instantiation inside that client method.

If the field should not be exposed by CLI, add it to `CLI_EXCLUDE_FIELDS`.
Relationship-backed filters may also need custom ORM join logic in the store
layer.

## Compatibility

Check compatibility separately for each payload role:

- Requests: adding a required field breaks callers that omit it. Optional fields
  with defaults usually preserve existing calls; check older servers too.
- Updates: preserve the distinction between an omitted field and explicit
  `None`; changing it can turn a partial update into an unintended overwrite.
- Responses: removing or renaming fields, changing types, or allowing `None`
  where callers expect a value can break clients.

Check old persisted data and rolling client/server versions. Use deprecation
periods and defaults when evolving supported contracts.
